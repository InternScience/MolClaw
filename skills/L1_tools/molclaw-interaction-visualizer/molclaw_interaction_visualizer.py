#!/usr/bin/env python3
"""
Protein-Ligand Interaction Analyzer
====================================
Pure Python/NumPy implementation covering:
  1. Hydrogen bonds
  2. Hydrophobic contacts
  3. π-π stacking (Face-to-Face & Edge-to-Face)
  4. Salt bridges
  5. Cation-π interactions
  6. Halogen bonds
  7. Metal coordination
  8. van der Waals contacts

Handles PDB, PDBQT, MOL2, SDF formats.
Automatically adds polar hydrogens when missing.
"""

import os
import re
import sys
import math
import warnings
from collections import defaultdict, namedtuple
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set

import numpy as np

# ============================================================================
# Data structures
# ============================================================================

class Atom:
    """Represents a single atom with all necessary properties."""
    __slots__ = [
        'idx', 'name', 'element', 'resname', 'resid', 'chain',
        'coord', 'charge', 'ad_type', 'is_hetatm',
        'hybridization', 'neighbors', 'is_aromatic',
        'is_hb_donor', 'is_hb_acceptor', 'is_hydrophobic',
        'is_positive', 'is_negative', 'is_metal', 'is_halogen',
        'attached_hydrogens', 'ring_ids'
    ]

    def __init__(self):
        self.idx = 0
        self.name = ""
        self.element = ""
        self.resname = ""
        self.resid = 0
        self.chain = ""
        self.coord = np.zeros(3)
        self.charge = 0.0
        self.ad_type = ""
        self.is_hetatm = False
        self.hybridization = ""
        self.neighbors: List[int] = []
        self.is_aromatic = False
        self.is_hb_donor = False
        self.is_hb_acceptor = False
        self.is_hydrophobic = False
        self.is_positive = False
        self.is_negative = False
        self.is_metal = False
        self.is_halogen = False
        self.attached_hydrogens: List[int] = []
        self.ring_ids: List[int] = []

    @property
    def res_label(self):
        return f"{self.resname}{self.resid}{self.chain}"

    def __repr__(self):
        return f"Atom({self.name}, {self.element}, {self.resname}{self.resid})"


class Ring:
    """Represents an aromatic ring."""
    def __init__(self, atom_indices: List[int], coords: np.ndarray):
        self.atom_indices = atom_indices
        self.coords = coords  # Nx3
        self.centroid = coords.mean(axis=0)
        self.normal = self._compute_normal()
        self.radius = np.linalg.norm(coords - self.centroid, axis=1).mean()
        self.res_label = ""  # filled in by caller

    def _compute_normal(self) -> np.ndarray:
        """Compute ring normal via SVD (robust for any ring size)."""
        centered = self.coords - self.centroid
        if len(centered) < 3:
            return np.array([0., 0., 1.])
        _, _, vh = np.linalg.svd(centered)
        normal = vh[-1]
        return normal / (np.linalg.norm(normal) + 1e-12)


# Interaction result types
Interaction = namedtuple('Interaction', [
    'type', 'subtype', 'atoms_lig', 'atoms_prot',
    'distance', 'angle', 'res_label', 'details'
])


# ============================================================================
# Constants
# ============================================================================

METALS = {'FE', 'ZN', 'MG', 'CA', 'MN', 'CO', 'CU', 'NI', 'CD', 'NA', 'K'}
HALOGENS = {'F', 'CL', 'BR', 'I'}

# Amino acid properties for charge assignment
POS_CHARGED_RESIDUES = {
    'ARG': ['NH1', 'NH2', 'NE', 'CZ'],
    'LYS': ['NZ'],
    'HIS': ['ND1', 'NE2'],  # can be positive when protonated
}
NEG_CHARGED_RESIDUES = {
    'ASP': ['OD1', 'OD2', 'CG'],
    'GLU': ['OE1', 'OE2', 'CD'],
}

# Standard amino acid aromatic rings
AROMATIC_RINGS = {
    'PHE': [['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ']],
    'TYR': [['CG', 'CD1', 'CD2', 'CE1', 'CE2', 'CZ']],
    'TRP': [['CG', 'CD1', 'NE1', 'CE2', 'CD2'], ['CD2', 'CE2', 'CE3', 'CZ2', 'CZ3', 'CH2']],
    'HIS': [['CG', 'ND1', 'CD2', 'CE1', 'NE2']],
}

# VdW radii (Å)
VDW_RADII = {
    'H': 1.20, 'C': 1.70, 'N': 1.55, 'O': 1.52, 'F': 1.47,
    'P': 1.80, 'S': 1.80, 'CL': 1.75, 'BR': 1.85, 'I': 1.98,
    'FE': 2.05, 'ZN': 1.39, 'MG': 1.73, 'CA': 2.31, 'MN': 2.05,
    'CO': 2.00, 'CU': 1.40, 'NI': 1.63, 'CD': 1.58, 'NA': 2.27,
    'K': 2.75, 'SE': 1.90,
}

# Thresholds (consolidated from ProLIF/PLIP/BINANA analysis)
THRESHOLDS = {
    'hbond_dist': 3.5,        # D···A distance
    'hbond_angle_min': 130,   # D-H···A angle min
    'hbond_angle_max': 180,
    'hydrophobic_dist': 4.5,
    'pistack_dist': 5.5,
    'pistack_ftf_angle_max': 35,    # plane angle for face-to-face
    'pistack_etf_angle_min': 50,    # plane angle for edge-to-face
    'pistack_etf_angle_max': 90,
    'pistack_normal_centroid_angle': 33,
    'pistack_etf_dist': 6.5,
    'saltbridge_dist': 5.5,
    'cation_pi_dist': 6.0,
    'cation_pi_angle_max': 30,
    'xbond_dist': 3.5,
    'xbond_axd_angle_min': 130,
    'xbond_axd_angle_max': 180,
    'xbond_xar_angle_min': 80,
    'xbond_xar_angle_max': 140,
    'metal_dist': 3.0,
    'vdw_tolerance': 0.5,
    'close_contact_dist': 4.0,
}


# ============================================================================
# File Parsers
# ============================================================================

VALID_ELEMENTS = {
    'H', 'C', 'N', 'O', 'F', 'P', 'S', 'CL', 'BR', 'I', 'SE',
    'FE', 'ZN', 'MG', 'CA', 'MN', 'CO', 'CU', 'NI', 'CD', 'NA', 'K',
    'HE', 'LI', 'BE', 'B', 'NE', 'AR', 'AL', 'SI', 'TI', 'V', 'CR',
    'AS', 'MO', 'AG', 'SN', 'PT', 'AU', 'HG', 'PB', 'W', 'BI',
}


def guess_element(atom_name: str, ad_type: str = "", line: str = "") -> str:
    """Guess element from atom name, AutoDock type, or PDB element column."""
    # Try AutoDock type FIRST (for PDBQT files)
    if ad_type:
        t = ad_type.strip().upper()
        mapping = {
            'A': 'C', 'C': 'C', 'N': 'N', 'NA': 'N', 'NS': 'N',
            'O': 'O', 'OA': 'O', 'OS': 'O', 'S': 'S', 'SA': 'S',
            'H': 'H', 'HD': 'H', 'HS': 'H', 'P': 'P',
            'F': 'F', 'CL': 'CL', 'BR': 'BR', 'I': 'I',
            'FE': 'FE', 'ZN': 'ZN', 'MG': 'MG', 'CA': 'CA',
            'MN': 'MN', 'CO': 'CO', 'CU': 'CU', 'NI': 'NI',
        }
        if t in mapping:
            return mapping[t]

    # Try PDB element column (cols 77-78) — only if it's a valid element
    if len(line) >= 78:
        el = line[76:78].strip().upper()
        # AutoDock atom types sometimes leak into the element column of
        # .pdb files that were converted from .pdbqt. Re-map them.
        AD_LEAK = {'NA':'N', 'NS':'N', 'OA':'O', 'OS':'O', 'SA':'S',
                   'HD':'H', 'HS':'H', 'A':'C'}
        if el in AD_LEAK:
            return AD_LEAK[el]
        if el and el in VALID_ELEMENTS:
            return el

    # From atom name
    name = atom_name.strip().upper()
    if not name:
        return 'C'
    # Handle cases like "1HG2", "2HD1"
    name_stripped = name.lstrip('0123456789')
    if not name_stripped:
        return 'C'
    first = name_stripped[0]
    if first == 'C':
        if len(name_stripped) > 1 and name_stripped[1] == 'L':
            return 'CL'
        return 'C'
    elif first == 'N':
        return 'N'
    elif first == 'O':
        return 'O'
    elif first == 'S':
        if len(name_stripped) > 1 and name_stripped[1] == 'E':
            return 'SE'
        return 'S'
    elif first == 'H':
        return 'H'
    elif first == 'F':
        if len(name_stripped) > 1 and name_stripped[1] == 'E':
            return 'FE'
        return 'F'
    elif first == 'B':
        if len(name_stripped) > 1 and name_stripped[1] == 'R':
            return 'BR'
        return 'C'  # fallback
    elif first == 'I':
        return 'I'
    elif first == 'P':
        return 'P'
    elif first in ('Z',):
        if len(name_stripped) > 1 and name_stripped[1] == 'N':
            return 'ZN'
        return name_stripped[:2] if len(name_stripped) > 1 else name_stripped
    elif first == 'M':
        if len(name_stripped) > 1:
            two = name_stripped[:2]
            if two in ('MG', 'MN'):
                return two
        return name_stripped[:2] if len(name_stripped) > 1 else name_stripped
    elif first == 'K':
        return 'K'
    else:
        return name_stripped[:2] if len(name_stripped) > 1 else name_stripped


def parse_pdb_pdbqt(filepath: str) -> List[Atom]:
    """Parse PDB or PDBQT file into list of Atoms. Takes first MODEL only."""
    atoms = []
    is_pdbqt = filepath.lower().endswith('.pdbqt')
    in_model = False
    first_model_done = False

    # Handle \r\n line endings
    with open(filepath, 'r') as f:
        raw = f.read()
    lines = raw.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    for line in lines:
        rec = line[:6].strip()

        if rec == 'MODEL':
            if first_model_done:
                break
            in_model = True
            continue
        if rec == 'ENDMDL':
            first_model_done = True
            continue

        if rec not in ('ATOM', 'HETATM'):
            continue

        a = Atom()
        a.idx = len(atoms)
        a.is_hetatm = (rec == 'HETATM')

        # Standard PDB columns
        a.name = line[12:16].strip()
        a.resname = line[17:20].strip()
        a.chain = line[21:22].strip()
        try:
            a.resid = int(line[22:26].strip())
        except (ValueError, IndexError):
            a.resid = 0

        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
            a.coord = np.array([x, y, z])
        except (ValueError, IndexError):
            continue

        # AutoDock type for PDBQT
        if is_pdbqt and len(line) >= 78:
            a.ad_type = line[77:].strip().split()[0] if len(line) > 77 else ""
            try:
                a.charge = float(line[70:76].strip())
            except (ValueError, IndexError):
                a.charge = 0.0

        a.element = guess_element(a.name, a.ad_type, line)
        atoms.append(a)

    return atoms


# ============================================================================
# Build connectivity and annotate properties
# ============================================================================

def build_connectivity(atoms: List[Atom], bond_tolerance: float = 0.45):
    """Build bonds based on distance and covalent radii."""
    COVALENT_RADII = {
        'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57,
        'P': 1.07, 'S': 1.05, 'CL': 1.02, 'BR': 1.20, 'I': 1.39,
        'SE': 1.20, 'FE': 1.32, 'ZN': 1.22, 'MG': 1.41, 'CA': 1.76,
        'MN': 1.39, 'CO': 1.26, 'CU': 1.32, 'NI': 1.24, 'CD': 1.44,
        'NA': 1.66, 'K': 2.03,
    }

    coords = np.array([a.coord for a in atoms])
    n = len(atoms)
    if n == 0:
        return

    # Use spatial bucketing for efficiency
    for i in range(n):
        atoms[i].neighbors = []

    # For small molecules, brute force is fine
    if n < 500:
        for i in range(n):
            ri = COVALENT_RADII.get(atoms[i].element, 1.5)
            for j in range(i + 1, n):
                rj = COVALENT_RADII.get(atoms[j].element, 1.5)
                max_d = ri + rj + bond_tolerance
                d = np.linalg.norm(coords[i] - coords[j])
                if d < max_d and d > 0.4:
                    atoms[i].neighbors.append(j)
                    atoms[j].neighbors.append(i)
    else:
        # For proteins, only build bonds within residues + peptide bonds
        # Group by (chain, resid)
        residue_map = defaultdict(list)
        for i, a in enumerate(atoms):
            residue_map[(a.chain, a.resid)].append(i)

        for key, indices in residue_map.items():
            for ii, i in enumerate(indices):
                ri = COVALENT_RADII.get(atoms[i].element, 1.5)
                for j in indices[ii+1:]:
                    rj = COVALENT_RADII.get(atoms[j].element, 1.5)
                    max_d = ri + rj + bond_tolerance
                    d = np.linalg.norm(coords[i] - coords[j])
                    if d < max_d and d > 0.4:
                        atoms[i].neighbors.append(j)
                        atoms[j].neighbors.append(i)

        # Peptide bonds (C-N between consecutive residues)
        c_atoms = {}  # (chain, resid) -> idx of C atom
        n_atoms = {}  # (chain, resid) -> idx of N atom
        for i, a in enumerate(atoms):
            if a.name == 'C' and a.element == 'C':
                c_atoms[(a.chain, a.resid)] = i
            elif a.name == 'N' and a.element == 'N':
                n_atoms[(a.chain, a.resid)] = i

        for (ch, rid), ci in c_atoms.items():
            ni = n_atoms.get((ch, rid + 1))
            if ni is not None:
                d = np.linalg.norm(coords[ci] - coords[ni])
                if d < 1.8:
                    atoms[ci].neighbors.append(ni)
                    atoms[ni].neighbors.append(ci)

    # Track attached hydrogens
    for i, a in enumerate(atoms):
        if a.element == 'H':
            for j in a.neighbors:
                atoms[j].attached_hydrogens.append(i)


def annotate_properties(atoms: List[Atom]):
    """Assign chemical properties: donor/acceptor/hydrophobic/charge/aromatic."""
    for a in atoms:
        el = a.element

        # Metals
        if el in METALS:
            a.is_metal = True
            a.is_positive = True
            continue

        # Halogens
        if el in HALOGENS:
            a.is_halogen = True
            if el == 'F':
                # F can be HB acceptor
                a.is_hb_acceptor = True
            continue

        # Nitrogen
        if el == 'N':
            neighbor_elements = [atoms[j].element for j in a.neighbors if j < len(atoms)]
            n_heavy = sum(1 for e in neighbor_elements if e != 'H')
            has_h = any(e == 'H' for e in neighbor_elements) or len(a.attached_hydrogens) > 0

            # HB donor if has H
            if has_h:
                a.is_hb_donor = True
            # HB acceptor: sp2/sp3 nitrogen not amide-like in most cases
            # Simplified: N with < 4 heavy neighbors
            if n_heavy <= 3:
                a.is_hb_acceptor = True

            # Charge from residue context
            if a.resname in POS_CHARGED_RESIDUES:
                if a.name in POS_CHARGED_RESIDUES[a.resname]:
                    a.is_positive = True

        # Oxygen
        elif el == 'O':
            a.is_hb_acceptor = True
            has_h = len(a.attached_hydrogens) > 0
            if has_h:
                a.is_hb_donor = True

            if a.resname in NEG_CHARGED_RESIDUES:
                if a.name in NEG_CHARGED_RESIDUES[a.resname]:
                    a.is_negative = True

        # Sulfur
        elif el == 'S':
            a.is_hb_acceptor = True
            if len(a.attached_hydrogens) > 0:
                a.is_hb_donor = True

        # Carbon — hydrophobic if only bonded to C/H
        elif el == 'C':
            neighbor_elements = set(atoms[j].element for j in a.neighbors if j < len(atoms))
            if neighbor_elements <= {'C', 'H', 'S', 'BR', 'I'}:
                a.is_hydrophobic = True

        # Phosphorus
        elif el == 'P':
            a.is_hb_acceptor = True

    # Additional: for PDBQT ligands, use AutoDock types
    for a in atoms:
        t = a.ad_type.upper()
        if t == 'OA':
            a.is_hb_acceptor = True
        elif t == 'OS':
            a.is_hb_acceptor = True
        elif t == 'NA':
            a.is_hb_acceptor = True
        elif t == 'NS':
            a.is_hb_acceptor = True
        elif t == 'SA':
            a.is_hb_acceptor = True
        elif t == 'HD':
            pass  # hydrogen on donor, handled via attached_hydrogens
        elif t == 'A':
            a.is_aromatic = True
            a.is_hydrophobic = True
        elif t == 'C':
            pass  # already handled above


def annotate_ligand_charges(atoms: List[Atom]):
    """Heuristic charge assignment for ligand atoms (no SMARTS available)."""
    for a in atoms:
        if a.element == 'N':
            neighbor_elements = [atoms[j].element for j in a.neighbors if j < len(atoms)]
            n_heavy = sum(1 for e in neighbor_elements if e != 'H')
            n_h = sum(1 for e in neighbor_elements if e == 'H')
            # Quaternary N or N with charge > 0 from PDBQT
            if a.charge > 0.2 or (n_heavy + n_h >= 4):
                a.is_positive = True
            # NH2 groups with positive partial charge
            if n_h >= 2 and a.charge > 0:
                a.is_positive = True
        elif a.element == 'O':
            if a.charge < -0.3:
                # Likely deprotonated carboxylate
                neighbor_elements = [atoms[j].element for j in a.neighbors if j < len(atoms)]
                if len(neighbor_elements) == 1 and neighbor_elements[0] == 'C':
                    a.is_negative = True


# ============================================================================
# Ring Detection
# ============================================================================

def find_rings_protein(atoms: List[Atom]) -> List[Ring]:
    """Find aromatic rings in protein using known residue templates."""
    rings = []
    # Group atoms by (chain, resid, resname)
    residue_map = defaultdict(dict)  # (chain, resid) -> {name: idx}
    for i, a in enumerate(atoms):
        residue_map[(a.chain, a.resid, a.resname)][a.name] = i

    for (chain, resid, resname), name_map in residue_map.items():
        if resname not in AROMATIC_RINGS:
            continue
        for ring_names in AROMATIC_RINGS[resname]:
            indices = []
            for n in ring_names:
                if n in name_map:
                    indices.append(name_map[n])
            if len(indices) >= 5:  # allow one missing atom
                coords = np.array([atoms[i].coord for i in indices])
                r = Ring(indices, coords)
                r.res_label = f"{resname}{resid}{chain}"
                rings.append(r)
                for i in indices:
                    atoms[i].is_aromatic = True
                    atoms[i].ring_ids.append(len(rings) - 1)
    return rings


def find_rings_ligand(atoms: List[Atom]) -> List[Ring]:
    """Find aromatic rings in ligand using BFS-based shortest path ring detection."""
    heavy_indices = [i for i, a in enumerate(atoms) if a.element != 'H']
    if len(heavy_indices) < 5:
        return []

    idx_set = set(heavy_indices)
    adj = defaultdict(set)
    for i in heavy_indices:
        for j in atoms[i].neighbors:
            if j in idx_set:
                adj[i].add(j)

    # Find SSSR using edge-removal + BFS
    rings_found = set()
    for i in heavy_indices:
        for j in adj[i]:
            if j <= i:
                continue
            # Remove edge i-j, find shortest path from i to j
            path = _bfs_path(adj, i, j, exclude_edge=(i, j))
            if path and 3 <= len(path) <= 7:
                ring_key = frozenset(path)
                rings_found.add(ring_key)

    # Filter: only keep 5- and 6-membered rings that are planar
    result = []
    for ring_set in rings_found:
        if len(ring_set) not in (5, 6):
            continue
        ring_idx_list = list(ring_set)
        # Order ring atoms by connectivity
        ordered = _order_ring(ring_idx_list, adj)
        if not ordered:
            continue
        coords = np.array([atoms[i].coord for i in ordered])
        r = Ring(ordered, coords)

        # Check planarity
        centered = coords - r.centroid
        _, s, _ = np.linalg.svd(centered)
        if len(s) >= 3 and s[-1] < 0.5:
            r.res_label = atoms[ordered[0]].res_label
            result.append(r)
            for i in ordered:
                atoms[i].is_aromatic = True
                atoms[i].ring_ids.append(len(result) - 1)

    return result


def _bfs_path(adj, start, end, exclude_edge):
    """BFS shortest path from start to end, excluding one edge."""
    from collections import deque
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        if len(path) > 7:
            continue
        for nb in adj[node]:
            # Skip the excluded edge
            if (node, nb) == exclude_edge or (nb, node) == exclude_edge:
                if node == start and nb == end:
                    continue
                if node == end and nb == start:
                    continue
            if nb == end:
                return path + [nb]
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, path + [nb]))
    return None


def _order_ring(indices, adj):
    """Order ring atoms by following adjacency."""
    idx_set = set(indices)
    if not indices:
        return None
    ordered = [indices[0]]
    remaining = set(indices[1:])
    for _ in range(len(indices) - 1):
        current = ordered[-1]
        found = False
        for nb in adj[current]:
            if nb in remaining:
                ordered.append(nb)
                remaining.remove(nb)
                found = True
                break
        if not found:
            return None
    # Verify last connects to first
    if ordered[0] not in adj[ordered[-1]]:
        return None
    return ordered


# ============================================================================
# Hydrogen Addition (when missing)
# ============================================================================

def add_polar_hydrogens(atoms: List[Atom], is_protein: bool = True) -> List[Atom]:
    """Add approximate polar hydrogens to N and O atoms that lack them."""
    new_atoms = []
    has_any_h = any(a.element == 'H' for a in atoms)

    if has_any_h:
        return atoms  # Already has hydrogens

    for i, a in enumerate(atoms):
        if a.element not in ('N', 'O', 'S'):
            continue

        neighbor_coords = [atoms[j].coord for j in a.neighbors if j < len(atoms)]
        if not neighbor_coords:
            continue

        n_needed = 0
        bond_len = 1.0

        if a.element == 'N':
            n_bonds = len(a.neighbors)
            if is_protein:
                # Backbone N gets 1H, NH2 in Arg/Lys etc.
                if a.name == 'N':
                    n_needed = 1
                elif a.name == 'NZ':  # Lys NH3+
                    n_needed = 3
                elif a.name in ('NH1', 'NH2'):  # Arg
                    n_needed = 2
                elif a.name in ('ND2', 'NE2', 'ND1', 'NE1', 'NE'):
                    n_needed = max(0, 1)
            else:
                # Simple heuristic for ligand N
                if n_bonds <= 2:
                    n_needed = 1
                elif n_bonds == 1:
                    n_needed = 2

        elif a.element == 'O':
            n_bonds = len(a.neighbors)
            if is_protein:
                if a.name in ('OG', 'OG1', 'OH', 'OE1', 'OE2', 'OD1', 'OD2'):
                    if a.resname in ('SER', 'THR', 'TYR'):
                        n_needed = 1
            else:
                if n_bonds == 1:
                    # Could be OH
                    nb = atoms[a.neighbors[0]]
                    if nb.element == 'C':
                        # Check if it's a carbonyl (C=O) or hydroxyl (C-OH)
                        # Heuristic: if C has another O neighbor, likely carboxyl
                        other_o = [atoms[k] for k in nb.neighbors
                                   if k < len(atoms) and atoms[k].element == 'O' and k != i]
                        if not other_o:
                            n_needed = 1

        elif a.element == 'S':
            if len(a.neighbors) == 1:
                n_needed = 1

        # Place hydrogens
        for h_idx in range(n_needed):
            h = Atom()
            h.idx = len(atoms) + len(new_atoms)
            h.name = f"H{len(a.attached_hydrogens) + h_idx + 1}"
            h.element = 'H'
            h.resname = a.resname
            h.resid = a.resid
            h.chain = a.chain
            h.is_hetatm = a.is_hetatm
            h.ad_type = 'HD'

            # Position: opposite to existing neighbors
            nb_coords = np.array(neighbor_coords)
            avg_dir = (nb_coords - a.coord).mean(axis=0)
            norm = np.linalg.norm(avg_dir)
            if norm > 0.01:
                h_dir = -avg_dir / norm
            else:
                h_dir = np.array([0., 0., 1.])

            # Add some offset for multiple H
            if h_idx > 0:
                perp = np.cross(h_dir, [1, 0, 0])
                if np.linalg.norm(perp) < 0.01:
                    perp = np.cross(h_dir, [0, 1, 0])
                perp = perp / np.linalg.norm(perp)
                angle = (h_idx * 120) * np.pi / 180
                h_dir = h_dir * np.cos(30 * np.pi / 180) + \
                        (perp * np.cos(angle) + np.cross(h_dir, perp) * np.sin(angle)) * np.sin(30 * np.pi / 180)
                h_dir = h_dir / np.linalg.norm(h_dir)

            h.coord = a.coord + h_dir * bond_len
            h.neighbors = [i]
            a.neighbors.append(h.idx)
            a.attached_hydrogens.append(h.idx)
            a.is_hb_donor = True
            new_atoms.append(h)

    atoms.extend(new_atoms)
    return atoms


# ============================================================================
# Geometry Utilities
# ============================================================================

def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at point b in degrees (a-b-c)."""
    v1 = a - b
    v2 = c - b
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-8 or n2 < 1e-8:
        return 0.0
    cos_angle = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def vec_angle_deg(v1: np.ndarray, v2: np.ndarray) -> float:
    """Angle between two vectors in degrees (0-180)."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-8 or n2 < 1e-8:
        return 0.0
    cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(abs(cos_a))))


def point_to_plane_dist(point: np.ndarray, plane_point: np.ndarray, normal: np.ndarray) -> float:
    """Distance from point to plane."""
    v = point - plane_point
    return abs(float(np.dot(v, normal)))


def project_onto_plane(point: np.ndarray, plane_point: np.ndarray, normal: np.ndarray) -> np.ndarray:
    """Project point onto plane."""
    v = point - plane_point
    d = np.dot(v, normal)
    return point - d * normal


# ============================================================================
# Interaction Detection
# ============================================================================

class InteractionDetector:
    def __init__(self, protein_atoms: List[Atom], ligand_atoms: List[Atom],
                 protein_rings: List[Ring], ligand_rings: List[Ring],
                 thresholds: dict = None):
        self.prot = protein_atoms
        self.lig = ligand_atoms
        self.prot_rings = protein_rings
        self.lig_rings = ligand_rings
        self.th = thresholds or THRESHOLDS
        self.interactions: List[Interaction] = []

        # Precompute coordinate arrays
        self.prot_coords = np.array([a.coord for a in self.prot]) if self.prot else np.empty((0, 3))
        self.lig_coords = np.array([a.coord for a in self.lig]) if self.lig else np.empty((0, 3))

        # Precompute distance matrix (lig x prot)
        if len(self.lig_coords) > 0 and len(self.prot_coords) > 0:
            diff = self.lig_coords[:, None, :] - self.prot_coords[None, :, :]
            self.dist_matrix = np.linalg.norm(diff, axis=2)
        else:
            self.dist_matrix = np.empty((0, 0))

    def detect_all(self) -> List[Interaction]:
        self.interactions = []
        self.detect_hydrogen_bonds()
        self.detect_hydrophobic()
        self.detect_pi_stacking()
        self.detect_salt_bridges()
        self.detect_cation_pi()
        self.detect_halogen_bonds()
        self.detect_metal_coordination()
        self.detect_vdw_contacts()
        return self.interactions

    # ---- Hydrogen Bonds ----
    def detect_hydrogen_bonds(self):
        """Detect hydrogen bonds using D-H···A geometry."""
        th = self.th
        all_atoms = self.lig + self.prot
        n_lig = len(self.lig)

        # Collect donors and acceptors with their source
        donors_lig = [(i, a) for i, a in enumerate(self.lig) if a.is_hb_donor]
        donors_prot = [(i + n_lig, a) for i, a in enumerate(self.prot) if a.is_hb_donor]
        acceptors_lig = [(i, a) for i, a in enumerate(self.lig) if a.is_hb_acceptor]
        acceptors_prot = [(i + n_lig, a) for i, a in enumerate(self.prot) if a.is_hb_acceptor]

        pairs = []
        # Lig donor → Prot acceptor
        for di, d in donors_lig:
            for ai, acc in acceptors_prot:
                pairs.append((di, d, ai, acc, 'LigDonor'))
        # Prot donor → Lig acceptor
        for di, d in donors_prot:
            for ai, acc in acceptors_lig:
                pairs.append((di, d, ai, acc, 'ProtDonor'))

        for di, donor, ai, acceptor, direction in pairs:
            d_a_dist = distance(donor.coord, acceptor.coord)
            if d_a_dist > th['hbond_dist'] + 0.6:  # loose pre-filter
                continue

            # Get hydrogen atoms
            h_indices = donor.attached_hydrogens
            if not h_indices:
                # No explicit H: use D-A distance only
                if d_a_dist <= th['hbond_dist']:
                    prot_a = acceptor if direction == 'LigDonor' else donor
                    lig_a = donor if direction == 'LigDonor' else acceptor
                    self.interactions.append(Interaction(
                        type='HBond', subtype=direction,
                        atoms_lig=[lig_a], atoms_prot=[prot_a],
                        distance=d_a_dist, angle=None,
                        res_label=prot_a.res_label,
                        details=f"{lig_a.name}···{prot_a.name} (no H, dist-only)"
                    ))
                continue

            for hi in h_indices:
                if hi >= len(all_atoms):
                    continue
                h_atom = all_atoms[hi]
                h_a_dist = distance(h_atom.coord, acceptor.coord)
                if h_a_dist > th['hbond_dist']:
                    continue
                # D-H···A angle
                dha_angle = angle_deg(donor.coord, h_atom.coord, acceptor.coord)
                if th['hbond_angle_min'] <= dha_angle <= th['hbond_angle_max']:
                    prot_a = acceptor if direction == 'LigDonor' else donor
                    lig_a = donor if direction == 'LigDonor' else acceptor
                    self.interactions.append(Interaction(
                        type='HBond', subtype=direction,
                        atoms_lig=[lig_a], atoms_prot=[prot_a],
                        distance=h_a_dist, angle=dha_angle,
                        res_label=prot_a.res_label,
                        details=f"{lig_a.name}···{prot_a.name} D-H···A={dha_angle:.1f}°"
                    ))
                    break  # one H-bond per donor to this acceptor

    # ---- Hydrophobic ----
    def detect_hydrophobic(self):
        th = self.th
        for i, la in enumerate(self.lig):
            if not la.is_hydrophobic and la.element != 'C':
                continue
            if la.element == 'H':
                continue
            for j, pa in enumerate(self.prot):
                if not pa.is_hydrophobic and pa.element != 'C':
                    continue
                if pa.element == 'H':
                    continue
                d = self.dist_matrix[i, j]
                if d <= th['hydrophobic_dist']:
                    # Only count C-C contacts
                    if la.element == 'C' and pa.element == 'C':
                        self.interactions.append(Interaction(
                            type='Hydrophobic', subtype='C-C',
                            atoms_lig=[la], atoms_prot=[pa],
                            distance=d, angle=None,
                            res_label=pa.res_label,
                            details=f"{la.name}···{pa.name}"
                        ))

    # ---- π-π Stacking ----
    def detect_pi_stacking(self):
        th = self.th
        for lr in self.lig_rings:
            for pr in self.prot_rings:
                d = distance(lr.centroid, pr.centroid)
                if d > th['pistack_etf_dist']:
                    continue

                # Angle between ring planes
                plane_angle = vec_angle_deg(lr.normal, pr.normal)

                # Normal-to-centroid angle
                centroid_vec = pr.centroid - lr.centroid
                nc_angle1 = vec_angle_deg(lr.normal, centroid_vec)
                nc_angle2 = vec_angle_deg(pr.normal, centroid_vec)
                nc_angle = min(nc_angle1, nc_angle2)

                # Face-to-Face
                if d <= th['pistack_dist'] and plane_angle <= th['pistack_ftf_angle_max']:
                    if nc_angle <= th['pistack_normal_centroid_angle']:
                        # Get residue label from protein ring
                        res_label = pr.res_label or "?"
                        lig_ring_names = ",".join(str(ai) for ai in lr.atom_indices[:3]) + "..."
                        prot_ring_names = ",".join(str(ai) for ai in pr.atom_indices[:3]) + "..."
                        self.interactions.append(Interaction(
                            type='PiStacking', subtype='FaceToFace',
                            atoms_lig=lr.atom_indices, atoms_prot=pr.atom_indices,
                            distance=d, angle=plane_angle,
                            res_label=res_label,
                            details=f"plane∠={plane_angle:.1f}° nc∠={nc_angle:.1f}°"
                        ))

                # Edge-to-Face
                if d <= th['pistack_etf_dist'] and \
                   th['pistack_etf_angle_min'] <= plane_angle <= th['pistack_etf_angle_max']:
                    if nc_angle <= 30:
                        res_label = pr.res_label or "?"
                        self.interactions.append(Interaction(
                            type='PiStacking', subtype='EdgeToFace',
                            atoms_lig=lr.atom_indices, atoms_prot=pr.atom_indices,
                            distance=d, angle=plane_angle,
                            res_label=res_label,
                            details=f"plane∠={plane_angle:.1f}° nc∠={nc_angle:.1f}°"
                        ))

    # ---- Salt Bridges ----
    def detect_salt_bridges(self):
        th = self.th
        # Collect charge centers
        pos_lig = [a for a in self.lig if a.is_positive]
        neg_lig = [a for a in self.lig if a.is_negative]
        pos_prot = [a for a in self.prot if a.is_positive]
        neg_prot = [a for a in self.prot if a.is_negative]

        # Lig+ ↔ Prot-
        seen = set()
        for pl in pos_lig:
            for np_ in neg_prot:
                d = distance(pl.coord, np_.coord)
                if d <= th['saltbridge_dist']:
                    key = (pl.idx, np_.res_label)
                    if key not in seen:
                        seen.add(key)
                        self.interactions.append(Interaction(
                            type='SaltBridge', subtype='Lig(+)Prot(-)',
                            atoms_lig=[pl], atoms_prot=[np_],
                            distance=d, angle=None,
                            res_label=np_.res_label,
                            details=f"{pl.name}(+)···{np_.name}(-)"
                        ))

        # Lig- ↔ Prot+
        for nl in neg_lig:
            for pp in pos_prot:
                d = distance(nl.coord, pp.coord)
                if d <= th['saltbridge_dist']:
                    key = (nl.idx, pp.res_label)
                    if key not in seen:
                        seen.add(key)
                        self.interactions.append(Interaction(
                            type='SaltBridge', subtype='Lig(-)Prot(+)',
                            atoms_lig=[nl], atoms_prot=[pp],
                            distance=d, angle=None,
                            res_label=pp.res_label,
                            details=f"{nl.name}(-)···{pp.name}(+)"
                        ))

    # ---- Cation-π ----
    def detect_cation_pi(self):
        th = self.th
        # Lig cation → Prot ring
        for a in self.lig:
            if not a.is_positive:
                continue
            for ring in self.prot_rings:
                d = distance(a.coord, ring.centroid)
                if d > th['cation_pi_dist']:
                    continue
                # Check angle between normal and cation-centroid vector
                vec = a.coord - ring.centroid
                ang = vec_angle_deg(ring.normal, vec)
                if ang <= th['cation_pi_angle_max']:
                    res_label = ring.res_label
                    self.interactions.append(Interaction(
                        type='CationPi', subtype='LigCation-ProtPi',
                        atoms_lig=[a], atoms_prot=[],
                        distance=d, angle=ang,
                        res_label=res_label,
                        details=f"{a.name}(+)···π({res_label})"
                    ))

        # Prot cation → Lig ring
        for a in self.prot:
            if not a.is_positive:
                continue
            for ring in self.lig_rings:
                d = distance(a.coord, ring.centroid)
                if d > th['cation_pi_dist']:
                    continue
                vec = a.coord - ring.centroid
                ang = vec_angle_deg(ring.normal, vec)
                if ang <= th['cation_pi_angle_max']:
                    self.interactions.append(Interaction(
                        type='CationPi', subtype='ProtCation-LigPi',
                        atoms_lig=[], atoms_prot=[a],
                        distance=d, angle=ang,
                        res_label=a.res_label,
                        details=f"π(lig)···{a.name}(+)"
                    ))

    # ---- Halogen Bonds ----
    def detect_halogen_bonds(self):
        th = self.th
        # Lig halogen → Prot acceptor
        for la in self.lig:
            if not la.is_halogen or la.element == 'F':
                continue  # F usually not halogen bond donor
            for pa in self.prot:
                if not pa.is_hb_acceptor:
                    continue
                d = distance(la.coord, pa.coord)
                if d > th['xbond_dist']:
                    continue

                # A···X-D angle (X=halogen, D=carbon bonded to it)
                for ni in la.neighbors:
                    if ni < len(self.lig) and self.lig[ni].element == 'C':
                        axd = angle_deg(pa.coord, la.coord, self.lig[ni].coord)
                        if th['xbond_axd_angle_min'] <= axd <= th['xbond_axd_angle_max']:
                            self.interactions.append(Interaction(
                                type='HalogenBond', subtype='XBond',
                                atoms_lig=[la], atoms_prot=[pa],
                                distance=d, angle=axd,
                                res_label=pa.res_label,
                                details=f"{la.name}(X)···{pa.name}(A) ∠={axd:.1f}°"
                            ))
                            break

    # ---- Metal Coordination ----
    def detect_metal_coordination(self):
        th = self.th
        coordinating_elements = {'N', 'O', 'S', 'F', 'CL', 'BR', 'I'}

        # Protein metals → Ligand coordinating atoms
        for pa in self.prot:
            if not pa.is_metal:
                continue
            for la in self.lig:
                if la.element not in coordinating_elements:
                    continue
                d = distance(pa.coord, la.coord)
                if d <= th['metal_dist']:
                    self.interactions.append(Interaction(
                        type='MetalCoord', subtype='ProtMetal-LigCoord',
                        atoms_lig=[la], atoms_prot=[pa],
                        distance=d, angle=None,
                        res_label=pa.res_label,
                        details=f"{pa.name}({pa.element})···{la.name}({la.element})"
                    ))

        # Ligand metals → Protein coordinating atoms
        for la in self.lig:
            if not la.is_metal:
                continue
            for pa in self.prot:
                if pa.element not in coordinating_elements:
                    continue
                d = distance(la.coord, pa.coord)
                if d <= th['metal_dist']:
                    self.interactions.append(Interaction(
                        type='MetalCoord', subtype='LigMetal-ProtCoord',
                        atoms_lig=[la], atoms_prot=[pa],
                        distance=d, angle=None,
                        res_label=pa.res_label,
                        details=f"{la.name}({la.element})···{pa.name}({pa.element})"
                    ))

    # ---- Van der Waals Contacts ----
    def detect_vdw_contacts(self):
        th = self.th
        count = 0
        vdw_by_res = defaultdict(int)
        for i, la in enumerate(self.lig):
            if la.element == 'H':
                continue
            r1 = VDW_RADII.get(la.element, 1.7)
            for j, pa in enumerate(self.prot):
                if pa.element == 'H':
                    continue
                r2 = VDW_RADII.get(pa.element, 1.7)
                d = self.dist_matrix[i, j]
                if d <= r1 + r2 + th['vdw_tolerance']:
                    vdw_by_res[pa.res_label] += 1
                    count += 1

        for res, cnt in sorted(vdw_by_res.items(), key=lambda x: -x[1])[:15]:
            self.interactions.append(Interaction(
                type='VdW', subtype='contact',
                atoms_lig=[], atoms_prot=[],
                distance=0, angle=None,
                res_label=res,
                details=f"{cnt} contacts"
            ))


# ============================================================================
# Filtering / Deduplication (PLIP-style)
# ============================================================================

def deduplicate_interactions(interactions: List[Interaction]) -> List[Interaction]:
    """Remove redundant interactions (e.g., salt bridge covers H-bond)."""
    # Find salt bridge residue pairs
    sb_pairs = set()
    for ix in interactions:
        if ix.type == 'SaltBridge':
            sb_pairs.add(ix.res_label)

    # Remove H-bonds that overlap with salt bridges
    filtered = []
    for ix in interactions:
        if ix.type == 'HBond' and ix.res_label in sb_pairs:
            # Check if it involves the same charged atoms
            # Keep it but mark as secondary
            ix = ix._replace(subtype=ix.subtype + ' (also SaltBridge)')
        filtered.append(ix)

    # Deduplicate hydrophobic: keep only closest per residue
    hydro_by_res = defaultdict(list)
    others = []
    for ix in filtered:
        if ix.type == 'Hydrophobic':
            hydro_by_res[ix.res_label].append(ix)
        else:
            others.append(ix)

    for res, ixs in hydro_by_res.items():
        best = min(ixs, key=lambda x: x.distance)
        others.append(best)

    # Deduplicate CationPi: keep only closest per (residue, cation_atom_name, subtype)
    catpi_by_key = defaultdict(list)
    others2 = []
    for ix in others:
        if ix.type == 'CationPi':
            # Use residue + subtype as key to keep only best
            catpi_by_key[(ix.res_label, ix.subtype)].append(ix)
        else:
            others2.append(ix)

    for key, ixs in catpi_by_key.items():
        best = min(ixs, key=lambda x: x.distance)
        others2.append(best)

    return others2


# ============================================================================
# Visualization
# ============================================================================


# ============================================================================
# PART II — Schrodinger-style visualization & decision-support layer
# (appended; self-contained; only depends on numpy + matplotlib + stdlib)
# ============================================================================
import argparse, csv, json, math
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from matplotlib.lines import Line2D
from matplotlib.path import Path as MplPath
from matplotlib import patches as mpatches

# ---- residue classification (drug-chemist-oriented) ------------------------
RES_CLASS = {
    # hydrophobic
    **{k:"hydrophobic" for k in ["ALA","VAL","LEU","ILE","MET","PRO","GLY","CYS"]},
    # aromatic
    **{k:"aromatic"    for k in ["PHE","TYR","TRP","HIS"]},
    # polar
    **{k:"polar"       for k in ["SER","THR","ASN","GLN"]},
    # positive
    **{k:"positive"    for k in ["LYS","ARG"]},
    # negative
    **{k:"negative"    for k in ["ASP","GLU"]},
}
RES_COLOR = {
    "hydrophobic":"#9CCAB0", "aromatic":"#7FB3D5", "polar":"#F5D76E",
    "positive":"#5DADE2",    "negative":"#E74C3C", "other":"#D5D8DC",
}
RES_EDGECOLOR = {
    "hydrophobic":"#2E7D4F", "aromatic":"#1F618D", "polar":"#B7950B",
    "positive":"#2874A6",    "negative":"#922B21", "other":"#7F8C8D",
}

# ---- interaction styling (Schrodinger-ish) ---------------------------------
INT_STYLE = {  # color, linestyle, width, legend label
    "HBond":       ("#C0392B", (0,(2,2)),  1.6, "H-bond"),
    "SaltBridge":  ("#7D3C98", (0,(6,3)),  1.8, "Salt bridge"),
    "PiStacking":  ("#1E8449", (0,(1,2)),  1.6, "π-π stacking"),
    "CationPi":    ("#2874A6", (0,(4,2,1,2)), 1.6, "Cation-π"),
    "Halogen":     ("#B9770E", (0,(2,3)),  1.6, "Halogen bond"),
    "Metal":       ("#6C3483", (0,(1,1)),  1.8, "Metal"),
    "Hydrophobic": ("#7F8C8D", (0,(1,4)),  1.0, "Hydrophobic"),
    "VdW":         ("#BDC3C7", (0,(1,6)),  0.7, "van der Waals"),
}
INT_ORDER = ["HBond","SaltBridge","PiStacking","CationPi","Halogen","Metal","Hydrophobic","VdW"]

def _norm_type(t):
    t = (t or "").lower()
    if "hbond" in t or "hydrogen" in t: return "HBond"
    if "salt" in t:                     return "SaltBridge"
    if "cation" in t and "pi" in t:     return "CationPi"
    if "pi" in t or "stack" in t:       return "PiStacking"
    if "halogen" in t:                  return "Halogen"
    if "metal" in t:                    return "Metal"
    if "hydrophobic" in t:              return "Hydrophobic"
    return "VdW"

def _res_class(resname):
    return RES_CLASS.get(resname.upper(), "other")


# ---------------------------------------------------------------------------
# Split a complex PDB into (receptor, partner) and run detection
# ---------------------------------------------------------------------------
def load_and_detect(pdb_path, mode, partner_chain=None, chain_a=None,
                    chain_b=None, ligand_resname=None):
    atoms = parse_pdb_pdbqt(pdb_path)
    if not atoms:
        raise ValueError(f"No atoms parsed from {pdb_path}")

    SKIP = {"HOH","WAT","TIP3","NA","CL","K","MG","ZN","SO4","PO4"}
    if mode == "ligand":
        if ligand_resname:
            part = [a for a in atoms if a.resname == ligand_resname]
            rec  = [a for a in atoms if a.resname != ligand_resname and not a.is_hetatm]
        else:
            part = [a for a in atoms if a.is_hetatm and a.resname not in SKIP]
            rec  = [a for a in atoms if not a.is_hetatm]
        label = ligand_resname or (part[0].resname if part else "LIG")
    elif mode == "peptide":
        assert partner_chain, "--partner_chain required"
        part = [a for a in atoms if a.chain == partner_chain and a.resname not in SKIP]
        rec  = [a for a in atoms if a.chain != partner_chain and not a.is_hetatm
                and a.resname not in SKIP]
        label = f"chain{partner_chain}"
    elif mode == "protein":
        assert chain_a and chain_b, "--chain_a and --chain_b required"
        rec  = [a for a in atoms if a.chain == chain_a and a.resname not in SKIP]
        part = [a for a in atoms if a.chain == chain_b and a.resname not in SKIP]
        label = f"{chain_a}-{chain_b}"
    else:
        raise ValueError(f"unknown mode {mode}")
    if not part:
        raise ValueError("Partner atom list empty — check chain/resname.")

    build_connectivity(rec)
    rec = add_polar_hydrogens(rec, is_protein=True)
    annotate_properties(rec)
    rec_rings = find_rings_protein(rec)

    build_connectivity(part)
    part_is_protein = (mode != "ligand")
    part = add_polar_hydrogens(part, is_protein=part_is_protein)
    if part_is_protein:
        annotate_properties(part)
        part_rings = find_rings_protein(part)
    else:
        annotate_ligand_charges(part)
        annotate_properties(part)
        part_rings = find_rings_ligand(part)

    analyzer = InteractionDetector(rec, part, rec_rings, part_rings)
    interactions = deduplicate_interactions(analyzer.detect_all())
    return rec, part, rec_rings, part_rings, interactions, label


# ---------------------------------------------------------------------------
# Decision-ready CSV export (geometry + per-residue rollup + per-atom site)
# ---------------------------------------------------------------------------
def export_csv(interactions, rec, part, out_csv, resid_offset=0, mode="ligand"):
    rows = []
    res_counts = defaultdict(lambda: defaultdict(int))
    res_best_dist = defaultdict(lambda: defaultdict(lambda: 99.))
    partner_site_counts = defaultdict(lambda: defaultdict(int))  # which ligand atom/resid contacts

    def _to_atoms(lst, pool):
        out = []
        for x in (lst or []):
            if hasattr(x, "resid"): out.append(x)       # already an Atom
            elif isinstance(x, int) and 0 <= x < len(pool): out.append(pool[x])
        return out

    for it in interactions:
        t = _norm_type(it.type)
        res = it.res_label
        prot_atoms_ix = _to_atoms(getattr(it, "atoms_prot", []), rec)
        lig_atoms_ix  = _to_atoms(getattr(it, "atoms_lig",  []), part)
        resid = prot_atoms_ix[0].resid if prot_atoms_ix else 0
        dist = getattr(it, "distance", None)
        ang  = getattr(it, "angle", None)
        rec_atom = ",".join(sorted({a.name for a in prot_atoms_ix}))
        par_atom = ",".join(sorted({a.name for a in lig_atoms_ix}))
        subtype  = getattr(it, "subtype", "") or ""
        res_counts[res][t] += 1
        if dist is not None and dist < res_best_dist[res][t]:
            res_best_dist[res][t] = dist
        if par_atom:
            partner_site_counts[par_atom][t] += 1
        rows.append({
            "type": t, "subtype": subtype,
            "rec_res": res,
            "rec_resid_pdb": resid,
            "rec_resid_mapped": resid + resid_offset if resid else "",
            "rec_res_class": _res_class(res[:3]),
            "rec_atom": rec_atom, "partner_atom": par_atom,
            "distance_A": f"{dist:.2f}" if dist is not None else "",
            "angle_deg":  f"{ang:.1f}"  if ang  is not None else "",
            "strength_hint": _strength_hint(t, dist, ang),
        })

    # per-interaction
    with open(out_csv, "w", newline="") as f:
        cols = ["type","subtype","rec_res","rec_resid_pdb","rec_resid_mapped",
                "rec_res_class","rec_atom","partner_atom","distance_A",
                "angle_deg","strength_hint"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)

    # per-residue rollup (decision sidecar)
    side = out_csv.replace(".csv","_residue_summary.csv")
    with open(side, "w", newline="") as f:
        cols = ["rec_res","rec_resid_mapped","rec_res_class"] + INT_ORDER + ["total","min_dist_A"]
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for res, c in sorted(res_counts.items(), key=lambda kv:-sum(kv[1].values())):
            # pick the most-informative mapped resid among rows of this residue
            rid = max((r["rec_resid_mapped"] for r in rows if r["rec_res"]==res
                       and r["rec_resid_mapped"] not in ("", 0)), default="")
            row = {"rec_res":res, "rec_resid_mapped":rid,
                   "rec_res_class":_res_class(res[:3]),
                   "total": sum(c.values()),
                   "min_dist_A": f"{min([d for d in res_best_dist[res].values() if d<99] or [0]):.2f}"}
            for t in INT_ORDER: row[t] = c.get(t, 0)
            w.writerow(row)

    # partner-site rollup (for small-molecule: which ligand atom is the hotspot for modification)
    if mode == "ligand":
        sidep = out_csv.replace(".csv","_partner_site.csv")
        with open(sidep, "w", newline="") as f:
            cols = ["partner_atom"] + INT_ORDER + ["total"]
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for pa, c in sorted(partner_site_counts.items(),
                                key=lambda kv:-sum(kv[1].values())):
                row = {"partner_atom": pa, "total": sum(c.values())}
                for t in INT_ORDER: row[t] = c.get(t, 0)
                w.writerow(row)
    return rows, res_counts, partner_site_counts

def _strength_hint(t, dist, ang):
    """Drug-chemist-style qualitative label, NOT a quantitative claim."""
    if t == "HBond" and dist is not None:
        if dist <= 2.9 and (ang is None or ang >= 150): return "strong"
        if dist <= 3.2 and (ang is None or ang >= 130): return "moderate"
        return "weak"
    if t == "SaltBridge" and dist is not None:
        return "strong" if dist <= 4.0 else "moderate"
    if t == "PiStacking" and dist is not None:
        return "strong" if dist <= 4.5 else "moderate"
    if t == "Hydrophobic": return "packing"
    if t == "VdW": return "contact"
    return ""


# ---------------------------------------------------------------------------
# PLOT 1 — Schrodinger-style 2D interaction diagram
#   Ligand heavy-atom skeleton drawn in the ligand coord plane (PCA projected
#   onto best-fit 2D), residues placed on a ring around the ligand with
#   color-coded bubbles, interaction edges styled by type.
# ---------------------------------------------------------------------------
# ---- default residue role annotations (EGFR-kinase subset; extendable) ----
DEFAULT_RESIDUE_ROLES = {
    "MET769":"Hinge", "LEU768":"Hinge", "THR766":"Gatekeeper",
    "LYS721":"Catalytic", "GLU738":"αC-helix", "ASP831":"DFG",
    "THR830":"DFG", "VAL702":"P-loop", "LEU820":"Hydrophobic",
    "ALA719":"Hydrophobic", "LEU694":"Hydrophobic", "MET742":"αC-helix",
    "LEU764":"β-sheet", "ILE720":"Catalytic", "ILE765":"β-sheet",
    "GLN767":"Hinge", "GLY772":"Hinge", "PHE771":"Aromatic",
    "PHE832":"DFG", "TYR251":"Aromatic",
}

# ============================================================================
# Atoms  →  RDKit Mol  →  proper 2D chemistry coords
# ============================================================================
def _atoms_to_rdkit_mol(lig_atoms):
    """Build an RDKit Mol from our internal Atom list + neighbors graph.

    We do NOT use 3D coords. We hand RDKit the atom list + bonds and let
    Compute2DCoords() generate proper cheminformatics-style 2D coordinates
    (fused rings as regular polygons, aromatic detection, zigzag chains).
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    heavy = [a for a in lig_atoms if a.element != "H"]
    if not heavy: return None, None
    idx_of = {id(a): i for i, a in enumerate(heavy)}

    rw = Chem.RWMol()
    atom_map = {}
    for i, a in enumerate(heavy):
        el = a.element.upper().capitalize()
        if len(el) == 2: el = el[0] + el[1].lower()
        try:
            rd_atom = Chem.Atom(el)
        except Exception:
            rd_atom = Chem.Atom(6)  # fallback C
        rd_atom.SetNoImplicit(False)
        aidx = rw.AddAtom(rd_atom)
        atom_map[i] = aidx

    # Bond orders: we don't have order info, so start with SINGLE; RDKit's
    # perception after sanitization will upgrade aromatic rings. For chains
    # containing double bonds we won't get them right — acceptable for
    # interaction-diagram purposes (the ligand skeleton is still readable).
    seen = set()
    for i, a in enumerate(heavy):
        for nb in a.neighbors:
            if 0 <= nb < len(lig_atoms):
                nb_a = lig_atoms[nb]
                if nb_a.element == "H": continue
                j = idx_of.get(id(nb_a))
                if j is None: continue
                key = tuple(sorted((i, j)))
                if key in seen: continue
                seen.add(key)
                rw.AddBond(atom_map[i], atom_map[j], Chem.BondType.SINGLE)

    mol = rw.GetMol()
    # Best-effort sanitize; if it fails, relax constraints
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        try:
            Chem.SanitizeMol(mol, sanitizeOps=(
                Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_KEKULIZE))
        except Exception:
            pass
    try:
        AllChem.Compute2DCoords(mol)
    except Exception:
        return None, None
    # Mapping index_in_heavy → (rdkit_atom_idx, Atom.name)
    atom_info = [(atom_map[i], heavy[i].name, heavy[i].element) for i in range(len(heavy))]
    return mol, atom_info


def _render_ligand_png(mol, size=(700, 700)):
    """Render ligand to a transparent-background PNG (in memory) using
    rdMolDraw2D, plus return the atom 2D coordinates (image-pixel frame)."""
    from rdkit.Chem.Draw import rdMolDraw2D
    drawer = rdMolDraw2D.MolDraw2DCairo(size[0], size[1])
    opt = drawer.drawOptions()
    opt.bondLineWidth = 2
    opt.baseFontSize = 0.7
    opt.padding = 0.07
    opt.clearBackground = False  # transparent
    opt.fixedBondLength = 28
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    import io
    from PIL import Image
    png_bytes = drawer.GetDrawingText()
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    # pixel coords for each atom
    atom_xy_px = []
    for idx in range(mol.GetNumAtoms()):
        p = drawer.GetDrawCoords(idx)
        atom_xy_px.append((p.x, p.y))
    return img, np.array(atom_xy_px), size


# ============================================================================
def _to_atom(x, atom_list):
    """atoms_lig entries may be Atom objects or int indices; normalize."""
    if x is None: return None
    if isinstance(x, int):
        return atom_list[x] if 0 <= x < len(atom_list) else None
    return x

# PLOT — Schrödinger-style 2D interaction diagram (RDKit ligand + residues)
# ============================================================================
def plot_2d_diagram(interactions, lig_atoms, out_png, title="",
                    score=None, delta_score=None, smiles=None,
                    residue_roles=None, ligand_scale=1.0):
    """Compose RDKit-rendered ligand + residue bubbles + interaction edges.

    Mirrors the Schrödinger / MolClaw reference diagram conventions:
      • ligand drawn with proper 2D chemistry coords (fused rings as polygons)
      • residue nodes labeled with functional role (Hinge / Gatekeeper / …)
      • H-bond lines annotated with atom pair (e.g. "N…OA")
      • legend bottom-right; score header; SMILES footer
    """
    if not lig_atoms:
        print("[WARN] no ligand atoms; skip 2D diagram"); return
    roles = {**DEFAULT_RESIDUE_ROLES, **(residue_roles or {})}

    mol, atom_info = _atoms_to_rdkit_mol(lig_atoms)
    if mol is None:
        print("[WARN] RDKit failed to build ligand mol; skip 2D diagram"); return
    # Atom.name-based lookup COLLIDES when a PDBQT file names every carbon "C".
    # Primary key = object identity; atom name kept only as soft fallback.
    heavy = [a for a in lig_atoms if a.element != "H"]
    obj_to_rdidx = {id(a): i for i, a in enumerate(heavy)}
    name_to_rdidx = {}  # fallback only
    for i, a in enumerate(heavy):
        name_to_rdidx.setdefault(a.name, i)

    # Render ligand image
    img_w, img_h = 720, 720
    img, atom_px, (W, H) = _render_ligand_png(mol, (img_w, img_h))
    # normalize px → data coords; ligand fills a 4.4-wide square (data units)
    # so it's legible relative to residue ring at R≈2.8-3.8
    LIG_HALF = 2.2 * ligand_scale
    def px_to_data(xy_px):
        x = (xy_px[:, 0] / W) * (2*LIG_HALF) - LIG_HALF
        y = LIG_HALF - (xy_px[:, 1] / H) * (2*LIG_HALF)
        return np.column_stack([x, y])
    atom_xy = px_to_data(atom_px)

    # group interactions by residue
    by_res = defaultdict(list)
    for it in interactions: by_res[it.res_label].append(it)
    if not by_res:
        print("[WARN] no interactions; skip 2D diagram"); return

    # place residues on a ring around ligand, sorted by mean angle of their anchor atoms
    angles = {}
    for res, ixs in by_res.items():
        pts = []
        for it in ixs:
            la = _to_atom((getattr(it, "atoms_lig", []) or [None])[0], lig_atoms)
            if la is None: continue
            ridx = obj_to_rdidx.get(id(la))
            if ridx is None: ridx = name_to_rdidx.get(la.name)
            if ridx is not None: pts.append(atom_xy[ridx])
        if pts: m = np.mean(pts, axis=0); angles[res] = math.atan2(m[1], m[0])
        else:   angles[res] = np.random.rand()*2*math.pi

    res_sorted = sorted(angles.items(), key=lambda kv: kv[1])
    n = len(res_sorted)
    R = max(3.8, 3.2 + 0.08*n)
    res_pos = {}
    for k, (res, _) in enumerate(res_sorted):
        th = 2*math.pi*k/n - math.pi/2
        res_pos[res] = np.array([R*math.cos(th), R*math.sin(th)])

    # --- figure ---
    fig, ax = plt.subplots(figsize=(13, 13), facecolor="white")
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-R-2.5, R+2.5); ax.set_ylim(-R-2.6, R+2.6)

    # header
    if title:
        ax.text(0, R+1.7, title, ha="center", va="center",
                fontsize=16, fontweight="bold", color="#1B2631")
    sub_bits = []
    if score is not None:       sub_bits.append(f"Score: {score:+.1f} kcal/mol")
    if delta_score is not None: sub_bits.append(f"ΔScore: {delta_score:+.1f}")
    if sub_bits:
        ax.text(0, R+1.35, "   |   ".join(sub_bits), ha="center", va="center",
                fontsize=11, color="#566573")

    # place ligand image in the centre
    ax.imshow(np.asarray(img), extent=[-LIG_HALF, LIG_HALF, -LIG_HALF, LIG_HALF],
              zorder=2, interpolation="bilinear")

    # residue bubbles (soft pastels matching reference)
    PASTEL = {"hydrophobic":("#CDEBC4","#5D8A66","Hydrophobic"),
              "aromatic":   ("#CFE2F3","#3D6A8E","Aromatic"),
              "polar":      ("#BED9E8","#2E5E7A","Polar"),
              "positive":   ("#C8D7E8","#355A89","Positive"),
              "negative":   ("#F5C6C6","#8B3A3A","Negative"),
              "other":      ("#E5E7E9","#6E7479","Other")}

    for res, pos in res_pos.items():
        cls = _res_class(res[:3])
        face, edge, _ = PASTEL.get(cls, PASTEL["other"])
        box = FancyBboxPatch((pos[0]-0.55, pos[1]-0.18), 1.10, 0.36,
                             boxstyle="round,pad=0.02,rounding_size=0.12",
                             facecolor=face, edgecolor=edge, lw=1.3, zorder=6)
        ax.add_patch(box)
        ax.text(pos[0], pos[1]+0.03, res, ha="center", va="center",
                fontsize=10, fontweight="bold", color="#1B2631", zorder=7)
        # role annotation underneath
        role = roles.get(res[:6]) or roles.get(res[:5]) or roles.get(res[:3])
        if role:
            ax.text(pos[0], pos[1]-0.28, role, ha="center", va="center",
                    fontsize=7.5, color=edge, style="italic", zorder=7)

        # interaction edges for this residue, grouped by type
        by_type = defaultdict(list)
        for it in by_res[res]: by_type[_norm_type(it.type)].append(it)

        # Type priority: the strongest interaction per residue wins; weaker
        # types are suppressed when a stronger one exists, to avoid visual
        # overlap of redundant edges/labels.
        PRIORITY = ["HBond","SaltBridge","PiStacking","CationPi",
                    "Halogen","Metal","Hydrophobic","VdW"]
        present = [t for t in PRIORITY if t in by_type]
        # Suppress VdW when any other type exists; suppress Hydrophobic when
        # HBond/SaltBridge already links to the same anchor atom.
        if len(present) > 1 and "VdW" in present: present.remove("VdW")
        if {"HBond","SaltBridge"} & set(present) and "Hydrophobic" in present:
            present.remove("Hydrophobic")

        for ti, t in enumerate(present):
            ixs = by_type[t]
            color, ls, lw, lab = INT_STYLE[t]
            # anchor = mean xy of ligand atoms involved in this interaction
            pts = []
            for it in ixs:
                la = _to_atom((getattr(it, "atoms_lig", []) or [None])[0], lig_atoms)
                if la is None: continue
                ridx = obj_to_rdidx.get(id(la))
                if ridx is None: ridx = name_to_rdidx.get(la.name)
                if ridx is not None: pts.append(atom_xy[ridx])
            anchor = np.mean(pts, axis=0) if pts else np.array([0.0, 0.0])

            # H-bond: thicker purple dashed + atom-pair annotation
            if t == "HBond":
                style_color, style_ls, style_lw = "#8E44AD", (0,(5,3)), 2.2
            elif t == "SaltBridge":
                style_color, style_ls, style_lw = "#7D3C98", (0,(4,2)), 2.2
            elif t == "Hydrophobic":
                style_color, style_ls, style_lw = "#2ECC71", "-", 1.4
            elif t == "VdW":
                style_color, style_ls, style_lw = "#95A5A6", (0,(1,3)), 0.9
            else:
                style_color, style_ls, style_lw = color, ls, lw

            arr = FancyArrowPatch(pos, anchor, arrowstyle="-",
                                  connectionstyle="arc3,rad=0.10",
                                  color=style_color, linewidth=style_lw,
                                  linestyle=style_ls, zorder=3, alpha=0.85)
            ax.add_patch(arr)

            # distance label (only for real geometry hits within physical cutoffs)
            MAX_DIST = {"HBond":4.0, "SaltBridge":5.5, "PiStacking":6.0,
                        "CationPi":6.0, "Halogen":4.5, "Hydrophobic":5.5,
                        "VdW":5.0}.get(t, 9.0)
            real = [x for x in ixs if getattr(x, "atoms_lig", None)
                    and (getattr(x,"distance",None) or 99.) < MAX_DIST]
            if real:
                d_best = min(getattr(x, "distance", 9.9) for x in real)
                # offset label position slightly by type-index to avoid overlap
                t_frac = 0.50 + 0.06 * ti
                mid = t_frac*pos + (1-t_frac)*anchor
                ax.text(mid[0], mid[1], f"{d_best:.1f}Å", fontsize=7.8,
                        color=style_color, ha="center", va="center",
                        fontstyle="italic",
                        bbox=dict(boxstyle="round,pad=0.08", fc="white",
                                  ec="none", alpha=0.78), zorder=8)
                # For H-bonds, annotate atom pair
                if t in ("HBond","SaltBridge"):
                    best = min(real, key=lambda x: getattr(x,"distance",9.9))
                    pa = (best.atoms_prot or [None])[0]
                    la = (best.atoms_lig  or [None])[0]
                    if pa and la:
                        ax.text(mid[0], mid[1]-0.18,
                                f"({pa.name}…{la.name})",
                                fontsize=6.8, color=style_color,
                                ha="center", va="center", zorder=8)

    # legend box (bottom-right)
    types_present = {_norm_type(it.type) for it in interactions}
    int_handles = []
    legend_map = [
        ("HBond",       "H-bond",       "#8E44AD", (0,(5,3)), 2.2),
        ("SaltBridge",  "Salt bridge",  "#7D3C98", (0,(4,2)), 2.2),
        ("PiStacking",  "π-π stacking", "#1E8449", (0,(1,2)), 1.6),
        ("Hydrophobic", "Hydrophobic",  "#2ECC71", "-",       1.4),
        ("Halogen",     "Halogen bond", "#B9770E", (0,(2,3)), 1.6),
        ("VdW",         "van der Waals","#95A5A6", (0,(1,3)), 0.9),
    ]
    for key, lab, c, ls, lw in legend_map:
        if key in types_present:
            int_handles.append(Line2D([0],[0], color=c, lw=lw, linestyle=ls, label=lab))
    res_handles = [mpatches.Patch(facecolor=PASTEL[k][0],
                                   edgecolor=PASTEL[k][1], label=f"{PASTEL[k][2]} residue")
                   for k in ["hydrophobic","aromatic","polar","positive","negative"]]
    leg = ax.legend(handles=int_handles + res_handles,
                    loc="lower right", bbox_to_anchor=(1.02, -0.02),
                    frameon=True, fontsize=9,
                    title="Interactions", title_fontsize=10,
                    edgecolor="#BDC3C7", labelspacing=0.6)
    leg.get_frame().set_alpha(0.95)

    # SMILES footer
    if smiles:
        ax.text(0, -R-1.7, smiles, ha="center", va="center",
                fontsize=8, color="#7F8C8D", family="monospace")

    plt.tight_layout(); plt.savefig(out_png, dpi=220, bbox_inches="tight",
                                    facecolor="white")
    plt.close()


# PLOT 2 — per-residue stacked bar (clean Schrodinger-ish palette)
# ---------------------------------------------------------------------------
def plot_residue_bar(res_counts, out_png, top_n=20, title=""):
    items = sorted(res_counts.items(), key=lambda kv:-sum(kv[1].values()))[:top_n]
    if not items:
        print("[WARN] empty res_counts"); return
    residues = [r for r,_ in items]
    fig, ax = plt.subplots(figsize=(max(7, len(residues)*0.5), 4.8),
                           facecolor="white")
    bottom = np.zeros(len(residues))
    for t in INT_ORDER:
        vals = np.array([items[i][1].get(t, 0) for i in range(len(items))])
        if vals.sum() == 0: continue
        ax.bar(residues, vals, bottom=bottom,
               color=INT_STYLE[t][0], label=INT_STYLE[t][3],
               edgecolor="white", linewidth=1.0, width=0.78)
        bottom += vals
    ax.set_ylabel("Interaction count", fontsize=11)
    ax.set_title(title or "Per-residue contact composition",
                 fontsize=12, fontweight="bold", pad=10)
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False, ncol=2)
    for s in ("top","right"): ax.spines[s].set_visible(False)
    plt.tight_layout(); plt.savefig(out_png, dpi=220, facecolor="white"); plt.close()


# ---------------------------------------------------------------------------
# PLOT 3 — interface residue × residue heatmap (peptide / protein)
# ---------------------------------------------------------------------------
def plot_interface_heatmap(rec, part, out_png, cutoff=4.5, title=""):
    rec_coords = np.array([a.coord for a in rec])
    par_coords = np.array([a.coord for a in part])
    if len(rec_coords)==0 or len(par_coords)==0: return
    D = np.linalg.norm(rec_coords[:,None,:]-par_coords[None,:,:], axis=2)
    pairs = np.argwhere(D < cutoff)
    if len(pairs)==0:
        print("[WARN] no contacts; skip heatmap"); return
    rk, pk = {}, {}
    for i,j in pairs:
        r = f"{rec[i].resname}{rec[i].resid}"
        p = f"{part[j].resname}{part[j].resid}"
        rk.setdefault(r, len(rk)); pk.setdefault(p, len(pk))
    M = np.zeros((len(rk), len(pk)), dtype=int)
    for i,j in pairs:
        r = f"{rec[i].resname}{rec[i].resid}"
        p = f"{part[j].resname}{part[j].resid}"
        M[rk[r], pk[p]] += 1
    fig, ax = plt.subplots(figsize=(max(5,0.38*len(pk)+2),
                                     max(5,0.30*len(rk)+2)),
                           facecolor="white")
    im = ax.imshow(M, aspect="auto", cmap="RdPu",
                   norm=matplotlib.colors.PowerNorm(gamma=0.6))
    ax.set_xticks(range(len(pk))); ax.set_xticklabels(list(pk), rotation=90, fontsize=7.5)
    ax.set_yticks(range(len(rk))); ax.set_yticklabels(list(rk), fontsize=7.5)
    ax.set_xlabel("Partner residue", fontsize=10)
    ax.set_ylabel("Receptor residue", fontsize=10)
    ax.set_title(title or f"Interface atom-pair contacts (<{cutoff} Å)",
                 fontsize=12, fontweight="bold", pad=10)
    cb = plt.colorbar(im, ax=ax, shrink=0.75); cb.set_label("atom-pair contacts", fontsize=9)
    plt.tight_layout(); plt.savefig(out_png, dpi=220, facecolor="white"); plt.close()


# ---------------------------------------------------------------------------
# PLOT 4 — 2D interface network (peptide / protein): bipartite spring layout
# ---------------------------------------------------------------------------
def plot_interface_network(interactions, part_atoms, out_png, title=""):
    by_edge = defaultdict(lambda: defaultdict(int))  # (rec_res, par_res) -> {type: count}
    for it in interactions:
        t = _norm_type(it.type)
        rec_res = it.res_label
        raw_la = (getattr(it, "atoms_lig", []) or [None])[0]
        la = _to_atom(raw_la, part_atoms)
        par_res = (f"{la.resname}{la.resid}" if la is not None
                   else f"PART:{getattr(it,'subtype','?')}")
        by_edge[(rec_res, par_res)][t] += 1
    if not by_edge:
        print("[WARN] no interface interactions; skip network"); return

    rec_nodes = sorted({e[0] for e in by_edge})
    par_nodes = sorted({e[1] for e in by_edge})
    # bipartite layout: receptor on left, partner on right
    def col_positions(nodes, x):
        n = len(nodes)
        ys = np.linspace(1, -1, n) if n>1 else [0]
        return {nd: np.array([x, y]) for nd, y in zip(nodes, ys)}
    pos = {**col_positions(rec_nodes, -1.0),
           **col_positions(par_nodes,  1.0)}

    fig, ax = plt.subplots(figsize=(9, max(5, 0.35*max(len(rec_nodes),len(par_nodes))+2)),
                           facecolor="white")
    ax.axis("off"); ax.set_xlim(-1.8, 1.8); ax.set_ylim(-1.25, 1.25)

    # edges
    for (r,p), tc in by_edge.items():
        total = sum(tc.values())
        # dominant type colors edge; width ~ total
        dom = max(tc, key=tc.get)
        col, ls, _, _ = INT_STYLE[dom]
        lw = 0.8 + 0.6*total
        arr = FancyArrowPatch(pos[r], pos[p], arrowstyle="-",
                              connectionstyle="arc3,rad=0.08",
                              color=col, linewidth=lw, linestyle=ls,
                              alpha=0.8, zorder=2)
        ax.add_patch(arr)

    # nodes
    for nd, (x,y) in pos.items():
        name3 = nd[:3]
        cls = _res_class(name3)
        box = FancyBboxPatch((x-0.28, y-0.055), 0.56, 0.11,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor=RES_COLOR[cls],
                             edgecolor=RES_EDGECOLOR[cls], lw=1.2, zorder=3)
        ax.add_patch(box)
        ax.text(x, y, nd, ha="center", va="center",
                fontsize=8.5, fontweight="bold", zorder=4)

    ax.text(-1.0, 1.18, "Receptor", ha="center", fontsize=11, fontweight="bold",
            color="#1B2631")
    ax.text( 1.0, 1.18, "Partner",  ha="center", fontsize=11, fontweight="bold",
            color="#1B2631")
    # legend
    handles = [Line2D([0],[0], color=INT_STYLE[t][0], lw=2.2,
                      linestyle=INT_STYLE[t][1], label=INT_STYLE[t][3])
               for t in INT_ORDER if any(t in tc for tc in by_edge.values())]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5,-0.05),
              ncol=len(handles), frameon=False, fontsize=9)
    ax.set_title(title or "Interface interaction network",
                 fontsize=12, fontweight="bold", pad=10)
    plt.tight_layout(); plt.savefig(out_png, dpi=220, facecolor="white"); plt.close()


# ---------------------------------------------------------------------------

# CLI
# ---------------------------------------------------------------------------
def _build_argparser():
    p = argparse.ArgumentParser(
        prog="molclaw-interaction-visualizer",
        description="Self-contained protein–ligand / peptide / protein-protein "
                    "interaction detector & Schrödinger-style visualizer.")
    p.add_argument("--complex",
                   help="Single PDB/PDBQT file containing receptor + partner. "
                        "Alternative: supply --receptor and --ligand (or "
                        "--partner_pdb) separately and let the script merge "
                        "them automatically.")
    p.add_argument("--receptor",
                   help="Receptor-only file (.pdb or .pdbqt). Used with "
                        "--ligand (for ligand mode) or --partner_pdb (for "
                        "peptide/protein modes). Overrides --complex.")
    p.add_argument("--ligand",
                   help="Ligand-only file (.sdf, .mol, .mol2, .pdb, .pdbqt, "
                        ".xyz). Used with --receptor in ligand mode. "
                        "Automatically converted + merged.")
    p.add_argument("--partner_pdb",
                   help="Partner-only protein/peptide PDB (for peptide or "
                        "protein modes when receptor and partner are in "
                        "separate files).")
    p.add_argument("--merged_out",
                   help="When auto-merging, also keep a copy of the merged "
                        "complex at this path (default: OUT_DIR/auto_merged.pdb).")
    p.add_argument("--mode", choices=["ligand","peptide","protein"],
                   default="ligand",
                   help="ligand: HETATM small molecule; peptide: partner is one "
                        "chain (short); protein: two full protein chains.")
    p.add_argument("--ligand_resname",
                   help="(ligand mode) restrict partner to a specific HETATM resname.")
    p.add_argument("--partner_chain",
                   help="(peptide mode) chain ID of the peptide.")
    p.add_argument("--chain_a", help="(protein mode) receptor chain.")
    p.add_argument("--chain_b", help="(protein mode) partner chain.")
    p.add_argument("--out_dir", default="viz_out",
                   help="Output directory (created if missing).")
    p.add_argument("--resid_offset", type=int, default=0,
                   help="Add to receptor resid in CSVs (L3 Principle 18 "
                        "PDB→UniProt offset).")
    p.add_argument("--top_n_bar", type=int, default=20,
                   help="Residues shown in stacked bar.")
    p.add_argument("--heatmap_cutoff", type=float, default=4.5,
                   help="Atom-pair cutoff (Å) for interface heatmap.")
    p.add_argument("--skip_diagram2d", action="store_true")
    p.add_argument("--skip_bar",       action="store_true")
    p.add_argument("--skip_heatmap",   action="store_true")
    p.add_argument("--skip_network",   action="store_true")
    p.add_argument("--skip_csv",       action="store_true")
    p.add_argument("--title", default="",
                   help="Common title prefix for figures.")
    p.add_argument("--score", type=float, default=None,
                   help="Docking score to display in 2D diagram header (kcal/mol).")
    p.add_argument("--delta_score", type=float, default=None,
                   help="ΔScore vs baseline for 2D diagram header.")
    p.add_argument("--smiles", default=None,
                   help="Ligand SMILES shown in the 2D diagram footer.")
    p.add_argument("--residue_roles_json", default=None,
                   help="JSON file: {\"MET769\":\"Hinge\", ...} role annotations.")
    p.add_argument("--ligand_scale", type=float, default=1.0,
                   help="Scale factor for the ligand drawing in the 2D "
                        "diagram (1.0=default, 1.3=larger, 0.8=smaller).")
    p.add_argument("--skip_pymol3d", action="store_true",
                   help="Skip headless PyMOL 3D multi-angle rendering.")
    p.add_argument("--pymol_views", type=int, default=4,
                   help="Number of 360°-orbit views for PyMOL renders (default 4).")
    p.add_argument("--pymol_width",  type=int, default=1400)
    p.add_argument("--pymol_height", type=int, default=1200)
    return p


def _read_structure_lines(path, ext):
    """Return a list of PDB-format lines from .pdb / .pdbqt / .pdb.gz / .ent / .cif.

    For .cif we convert to PDB via RDKit/PyMOL (whichever is available); for
    everything else we just parse text directly.
    """
    path = str(path)
    if path.endswith(".gz"):
        import gzip
        with gzip.open(path, "rt") as f: raw = f.readlines()
        return raw
    if ext in (".cif", ".mmcif"):
        # Use PyMOL as a universal converter: load cif, save pdb
        try:
            import subprocess, tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".pdb", delete=False).name
            r = subprocess.run(["pymol","-cq","-d",
                                f"load {path}; save {tmp}"],
                               capture_output=True, text=True, timeout=60)
            with open(tmp) as f: raw = f.readlines()
            Path(tmp).unlink(missing_ok=True)
            return raw
        except Exception:
            raise RuntimeError(f"Cannot parse CIF {path}: PyMOL conversion failed")
    # .pdb / .pdbqt / .ent — read as plain text
    with open(path) as f: return f.readlines()


def _auto_merge_inputs(args, out_dir):
    """Build a single complex PDB from --receptor + --ligand/--partner_pdb.

    Accepts common ligand formats: .sdf, .mol, .mol2, .pdb, .pdbqt, .xyz.
    Returns (merged_path, ligand_resname_used).
    """
    rec_path = args.receptor
    assert rec_path and Path(rec_path).exists(), \
        f"--receptor file not found: {rec_path}"

    merged = Path(args.merged_out) if args.merged_out else \
             Path(out_dir) / "auto_merged.pdb"
    merged.parent.mkdir(parents=True, exist_ok=True)

    # Gather receptor lines (drop any END/CONECT/MASTER).
    # Accepts .pdb / .pdbqt / .pdb.gz / .cif (via PyMOL).
    rec_ext = Path(rec_path).suffix.lower()
    if rec_ext == ".gz":
        rec_ext = Path(rec_path.rstrip(".gz")).suffix.lower()  # e.g. .pdb.gz → .pdb
    rec_lines = _read_structure_lines(rec_path, rec_ext)
    rec_out = [L for L in rec_lines
               if not L.startswith(("END", "CONECT", "MASTER"))]

    partner_lines = []
    lig_resname = args.ligand_resname or "LIG"

    if args.mode == "ligand":
        lig_path = args.ligand
        assert lig_path and Path(lig_path).exists(), \
            f"--ligand required in ligand mode when --complex absent: {lig_path}"
        ext = Path(lig_path).suffix.lower()

        if ext in (".sdf", ".mol", ".mol2"):
            # Use RDKit to parse + write a clean HETATM block with unique names
            try:
                from rdkit import Chem
            except ImportError:
                raise RuntimeError("RDKit needed to convert .sdf/.mol/.mol2. "
                                   "Install: pip install rdkit")
            if ext == ".mol2":
                mol = Chem.MolFromMol2File(lig_path, removeHs=True, sanitize=True)
            else:
                mol = Chem.MolFromMolFile(lig_path, removeHs=True, sanitize=True)
            if mol is None:
                raise RuntimeError(f"RDKit could not parse {lig_path}")
            # Give each atom a unique name (C1, C2, N1, O1, …)
            cnt = defaultdict(int)
            for a in mol.GetAtoms():
                mi = Chem.AtomPDBResidueInfo()
                mi.SetResidueName(lig_resname)
                mi.SetResidueNumber(1)
                mi.SetChainId("X")
                mi.SetIsHeteroAtom(True)
                el = a.GetSymbol(); cnt[el] += 1
                mi.SetName(f" {el}{cnt[el]:<2}"[:4])
                a.SetMonomerInfo(mi)
            tmp_pdb = merged.parent / "_lig_tmp.pdb"
            Chem.MolToPDBFile(mol, str(tmp_pdb), flavor=2)
            with open(tmp_pdb) as f: raw = f.readlines()
            partner_lines = [L for L in raw if L.startswith("HETATM")]
            tmp_pdb.unlink()

        elif ext in (".pdb", ".pdbqt"):
            with open(lig_path) as f: raw = f.readlines()
            # Extract first MODEL if multi-pose PDBQT
            if any(L.startswith("MODEL") for L in raw):
                cur = []; in_model = False
                for L in raw:
                    if L.startswith("MODEL"): in_model = True; continue
                    if L.startswith("ENDMDL"): break
                    if in_model and L.startswith(("ATOM","HETATM")):
                        cur.append(L)
                if not cur:  # fallback if no MODEL found
                    cur = [L for L in raw if L.startswith(("ATOM","HETATM"))]
                raw = cur
            # Convert any ATOM records to HETATM (ligand should be HETATM)
            partner_lines = []
            for L in raw:
                if L.startswith(("ATOM","HETATM")):
                    # force HETATM, set resname if blank/unknown
                    L = "HETATM" + L[6:]
                    rn = L[17:20].strip()
                    if not rn or rn in ("UNK",""):
                        L = L[:17] + f"{lig_resname:<3}" + L[20:]
                    partner_lines.append(L)

        elif ext == ".xyz":
            # Minimal XYZ → PDB conversion (requires RDKit for bond perception)
            try:
                from rdkit import Chem
                from rdkit.Chem import AllChem
            except ImportError:
                raise RuntimeError("RDKit needed for .xyz input")
            mol = Chem.MolFromXYZFile(lig_path)
            if mol is None:
                raise RuntimeError(f"RDKit could not parse XYZ: {lig_path}")
            try:
                from rdkit.Chem import rdDetermineBonds
                rdDetermineBonds.DetermineBonds(mol, charge=0)
            except Exception as e:
                print(f"[WARN] bond determination failed on XYZ: {e}")
            cnt = defaultdict(int)
            for a in mol.GetAtoms():
                mi = Chem.AtomPDBResidueInfo()
                mi.SetResidueName(lig_resname); mi.SetResidueNumber(1)
                mi.SetChainId("X"); mi.SetIsHeteroAtom(True)
                el = a.GetSymbol(); cnt[el] += 1
                mi.SetName(f" {el}{cnt[el]:<2}"[:4])
                a.SetMonomerInfo(mi)
            tmp_pdb = merged.parent / "_lig_tmp.pdb"
            Chem.MolToPDBFile(mol, str(tmp_pdb), flavor=2)
            with open(tmp_pdb) as f: raw = f.readlines()
            partner_lines = [L for L in raw if L.startswith("HETATM")]
            tmp_pdb.unlink()
        else:
            raise RuntimeError(f"Unsupported ligand format: {ext}")

    else:  # peptide / protein mode: partner is a protein chain file
        part_path = args.partner_pdb
        assert part_path and Path(part_path).exists(), \
            f"--partner_pdb required for {args.mode} mode when --complex absent"
        ext = Path(part_path).suffix.lower()
        raw = _read_structure_lines(part_path, ext)

        # Optionally restrict partner to a specific chain if user asked
        # (e.g. partner file has multiple chains and only one is the partner)
        pick = args.partner_chain if args.mode == "peptide" else args.chain_b
        if pick:
            cand = [L for L in raw
                    if L.startswith(("ATOM","HETATM")) and L[21] == pick]
            if cand: raw = cand
        # If the partner file uses the same chain id as receptor,
        # rename partner chain to avoid collision.
        target_chain = pick or "Z"
        rec_chains = {L[21] for L in rec_out if L.startswith(("ATOM","HETATM"))}
        if target_chain in rec_chains:
            for c in "ZYXWVUTSRQPONMLKJIHGFEDCBA":
                if c not in rec_chains:
                    target_chain = c; break
        partner_lines = []
        for L in raw:
            if L.startswith(("ATOM","HETATM")):
                # overwrite chain id col (22nd char, 0-indexed 21)
                L = L[:21] + target_chain + L[22:]
                partner_lines.append(L)
        # rewrite args so downstream uses the correct chain
        if args.mode == "peptide":
            args.partner_chain = target_chain
        else:
            args.chain_b = target_chain
            args.chain_a = args.chain_a or sorted(rec_chains)[0]

    with open(merged, "w") as f:
        f.writelines(rec_out)
        f.writelines(partner_lines)
        f.write("END\n")
    print(f"[INFO] auto-merged receptor + partner → {merged}  "
          f"(receptor lines: {len(rec_out)}, partner lines: {len(partner_lines)})")

    # If ligand mode and user didn't specify --ligand_resname, set it to what we used
    if args.mode == "ligand" and not args.ligand_resname:
        args.ligand_resname = lig_resname

    return str(merged)


def run_cli():
    args = _build_argparser().parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)

    # Auto-merge if --complex not given
    if not args.complex:
        assert args.receptor, \
            "Either --complex or --receptor (+ --ligand/--partner_pdb) is required."
        args.complex = _auto_merge_inputs(args, out_dir=out)

    rec, part, rec_rings, part_rings, interactions, label = load_and_detect(
        args.complex, args.mode,
        partner_chain=args.partner_chain, chain_a=args.chain_a,
        chain_b=args.chain_b, ligand_resname=args.ligand_resname)

    print(f"[INFO] mode={args.mode}  receptor={len(rec)}atoms  "
          f"partner={len(part)}atoms ({label})")
    print(f"[INFO] {len(interactions)} non-redundant interactions detected")

    ttl = (args.title + " — ") if args.title else ""
    rows, res_counts, site_counts = [], {}, {}
    csv_path = out / f"interactions_{label}.csv"
    if not args.skip_csv:
        rows, res_counts, site_counts = export_csv(
            interactions, rec, part, str(csv_path),
            resid_offset=args.resid_offset, mode=args.mode)

    if args.mode == "ligand" and not args.skip_diagram2d:
        rr = None
        if args.residue_roles_json and Path(args.residue_roles_json).exists():
            rr = json.load(open(args.residue_roles_json))
        plot_2d_diagram(interactions, part,
                        str(out / f"diagram2d_{label}.png"),
                        title=f"{ttl}2D interaction diagram ({label})",
                        score=args.score, delta_score=args.delta_score,
                        smiles=args.smiles, residue_roles=rr,
                        ligand_scale=args.ligand_scale)

    if res_counts and not args.skip_bar:
        plot_residue_bar(res_counts, str(out / f"residue_bar_{label}.png"),
                         top_n=args.top_n_bar,
                         title=f"{ttl}Per-residue contacts ({label})")

    if args.mode in ("peptide","protein"):
        if not args.skip_heatmap:
            plot_interface_heatmap(rec, part,
                                   str(out / f"interface_heatmap_{label}.png"),
                                   cutoff=args.heatmap_cutoff,
                                   title=f"{ttl}Interface contacts ({label})")
        if not args.skip_network:
            plot_interface_network(interactions, part,
                                   str(out / f"interface_network_{label}.png"),
                                   title=f"{ttl}Interface network ({label})")

    # decision summary JSON (agent-readable)
    pymol_outputs = []
    if not args.skip_pymol3d:
        try:
            pml = render_3d_pymol(
                pdb_path=args.complex, mode=args.mode, label=label,
                interactions=interactions, rec_atoms=rec, part_atoms=part,
                out_dir=str(out),
                ligand_resname=args.ligand_resname,
                resid_offset=args.resid_offset,
                chain_a=args.chain_a, chain_b=args.chain_b,
                partner_chain=args.partner_chain,
                run=True, img_size=min(args.pymol_width, args.pymol_height))
            pymol_outputs = [pml]
        except Exception as e:
            import traceback
            print(f"[WARN] PyMOL 3D render failed: {e}")
            traceback.print_exc(limit=2)
    summary = {
        "mode": args.mode, "label": label,
        "n_interactions": len(interactions),
        "n_contact_residues": len(res_counts),
        "interaction_type_counts": {
            t: sum(1 for it in interactions if _norm_type(it.type)==t) for t in INT_ORDER
        },
        "top_residues": [
            {"res": r, "class": _res_class(r[:3]),
             "total": sum(c.values()),
             "by_type": {k:v for k,v in c.items() if v}}
            for r, c in sorted(res_counts.items(),
                               key=lambda kv:-sum(kv[1].values()))[:10]
        ],
        "hot_partner_sites": ([
            {"partner_atom": pa, "total": sum(c.values()),
             "by_type": {k:v for k,v in c.items() if v}}
            for pa, c in sorted(site_counts.items(),
                                key=lambda kv:-sum(kv[1].values()))[:8]
        ] if site_counts else []),
        "outputs": {k: str(out / v) for k, v in {
            "interactions_csv":   f"interactions_{label}.csv",
            "residue_summary":    f"interactions_{label}_residue_summary.csv",
            "partner_site_csv":   f"interactions_{label}_partner_site.csv" if args.mode=="ligand" else None,
            "diagram2d":          f"diagram2d_{label}.png" if args.mode=="ligand" else None,
            "residue_bar":        f"residue_bar_{label}.png",
            "interface_heatmap":  f"interface_heatmap_{label}.png" if args.mode!="ligand" else None,
            "interface_network":  f"interface_network_{label}.png" if args.mode!="ligand" else None,
        }.items() if v},
    }
    with open(out / f"summary_{label}.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[DONE] → {out.resolve()}")



# ============================================================================
# PART III — 3D multi-angle PyMOL visualization
# Generates a .pml script that loads the complex, shows cartoon + sticks for
# interface residues, draws distance objects colored by interaction type, and
# renders 3 ray-traced PNGs from orthogonal angles. Optionally runs PyMOL.
# ============================================================================
import subprocess, shutil, tempfile

# PyMOL color names per interaction type (matches 2D diagram palette)
PML_COLORS = {
    "HBond":       "red",
    "SaltBridge":  "purple",
    "PiStacking":  "forest",
    "CationPi":    "deepteal",
    "Halogen":     "orange",
    "Metal":       "magenta",
    "Hydrophobic": "limegreen",
    "VdW":         "grey70",
}

def _pml_select_expr(atom):
    """Build a PyMOL selection string for a single atom."""
    ch = atom.chain or ""
    chstr = f"chain {ch} and " if ch else ""
    return f"({chstr}resi {atom.resid} and name {atom.name})"

def _write_pml(pdb_path, mode, label, interactions,
               partner_selection, receptor_selection, out_dir,
               ligand_resname=None, resid_offset=0,
               title="", img_size=1200):
    """Write a PyMOL .pml script and return its path.

    Produces 3 ray-traced images (front/side/top) plus the raw .pse session.
    """
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    pml_path = out_dir / f"scene_{label}.pml"
    abs_pdb  = str(Path(pdb_path).resolve())

    lines = [
        "# Auto-generated by molclaw-interaction-visualizer 3D module",
        f"# Mode: {mode}   Label: {label}",
        "bg_color white",
        "set ray_opaque_background, on",
        "set ray_shadows, 0",
        "set antialias, 2",
        "set cartoon_transparency, 0.15",
        "set stick_radius, 0.18",
        "set dash_width, 2.5",
        "set dash_gap, 0.25",
        "set label_size, 14",
        "set label_color, black",
        "set label_outline_color, white",
        "set label_font_id, 7",
        "set label_position, (0,0,3)",
        "",
        f'load {abs_pdb}, complex',
        "hide everything, complex",
        "",
        f"# receptor / partner selections",
        f"select receptor, complex and ({receptor_selection})",
        f"select partner,  complex and ({partner_selection})",
        "",
        "# cartoon for protein bodies",
        "show cartoon, receptor",
        "color grey80, receptor",
    ]

    if mode == "ligand":
        # Collect ligand atoms that participate in at least one interaction,
        # so we label only the "hot" atoms instead of the whole molecule.
        hot_lig_names = sorted({a.name for it in interactions
                                for a in (it.atoms_lig or [])
                                if hasattr(a, "name")})
        lines += [
            "show sticks, partner",
            "color cyan, partner and elem C",
            "util.cnc partner",   # standard heteroatom colors
        ]
        if hot_lig_names:
            sel = "partner and name " + "+".join(hot_lig_names)
            lines += [
                f"select hot_lig, {sel}",
                "label hot_lig, '%s' % (name)",
                "set label_color, darkblue, hot_lig",
            ]
    else:
        # peptide / protein-protein: partner gets cartoon + interface-sticks
        lines += [
            "show cartoon, partner",
            "color salmon, partner",
            "set cartoon_transparency, 0.25, partner",
        ]

    # Collect interface residues (receptor side) and optional partner side
    rec_resids = sorted({a.resid for it in interactions for a in (it.atoms_prot or [])
                         if hasattr(a, "resid")})
    part_resids = sorted({a.resid for it in interactions for a in (it.atoms_lig or [])
                          if hasattr(a, "resid")})
    if rec_resids:
        sel = "receptor and resi " + "+".join(str(r) for r in rec_resids)
        lines += [
            f"select iface_rec, {sel}",
            "show sticks, iface_rec and not (name C+N+O+H)",
            "color wheat, iface_rec and elem C",
            "util.cnc iface_rec",
            # three-letter residue label at CA
            "label iface_rec and name CA, '%s%s' % (resn, resi)",
        ]
    if mode != "ligand" and part_resids:
        sel = "partner and resi " + "+".join(str(r) for r in part_resids)
        lines += [
            f"select iface_part, {sel}",
            "show sticks, iface_part and not (name C+N+O+H)",
            "color palecyan, iface_part and elem C",
            "util.cnc iface_part",
            "label iface_part and name CA, '%s%s' % (resn, resi)",
        ]

    lines += ["", "# interaction distances, grouped by type"]
    dist_groups = defaultdict(list)  # type -> list of (sel1, sel2) tuples
    for it in interactions:
        t = _norm_type(it.type)
        ra = (it.atoms_prot or [None])[0]
        la = (it.atoms_lig  or [None])[0]
        # Both ends must be resolvable Atom objects (not ints) to draw
        if ra is None or la is None or isinstance(ra, int) or isinstance(la, int):
            continue
        dist_groups[t].append((ra, la, it))

    # Priority: draw stronger interactions last (on top)
    TYPE_DRAW_ORDER = ["VdW", "Hydrophobic", "PiStacking", "CationPi",
                       "Halogen", "Metal", "SaltBridge", "HBond"]
    for t in TYPE_DRAW_ORDER:
        pairs = dist_groups.get(t, [])
        if not pairs: continue
        obj = f"ix_{t.lower()}"
        lines.append(f"# --- {t} ({len(pairs)}) ---")
        # Skip VdW in 3D view to reduce visual noise (usually 20+ lines)
        if t == "VdW":
            lines.append(f"# (VdW contacts omitted in 3D view to reduce clutter)")
            continue
        for k, (ra, la, it) in enumerate(pairs):
            s1 = _pml_select_expr(ra)
            s2 = _pml_select_expr(la)
            lines.append(f'distance {obj}_{k}, {s1}, {s2}')
        lines.append(f"group {obj}, {obj}_*")
        lines.append(f"color {PML_COLORS[t]}, {obj}")
        if t in ("Hydrophobic", "VdW"):
            lines.append(f"set dash_radius, 0.06, {obj}")
        else:
            lines.append(f"set dash_radius, 0.10, {obj}")
    lines.append("hide labels, ix_*")   # don't show auto-distance numeric labels

    # zoom on interface
    lines += [
        "",
        "# view setup",
        "zoom polymer and (byres partner around 5), 4",
        "orient polymer and (byres partner around 5)",
        "set ray_trace_mode, 1",
        "",
    ]

    # Multi-angle rendering
    views = [
        ("front", "# initial orientation"),
        ("side",  "rotate y, 90"),
        ("top",   "rotate x, 90"),
    ]
    for name, cmd in views:
        png = out_dir / f"pymol_{label}_{name}.png"
        lines += [
            cmd,
            f'ray {img_size}, {img_size}',
            f'png {png.resolve()}, dpi=200',
        ]
    # end of script

    with open(pml_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return pml_path


def render_3d_pymol(pdb_path, mode, label, interactions, rec_atoms, part_atoms,
                    out_dir, ligand_resname=None, resid_offset=0,
                    chain_a=None, chain_b=None, partner_chain=None,
                    run=True, img_size=1200):
    """Public entry-point for 3D PyMOL visualization.

    Writes a .pml script and (if `run` and `pymol` on PATH) executes PyMOL
    in batch mode (`pymol -cq`) to produce 3 ray-traced PNGs + a .pse session.
    """
    # Build PyMOL selection strings for receptor / partner
    if mode == "ligand":
        if ligand_resname:
            partner_sel = f"resn {ligand_resname}"
        else:
            partner_sel = "hetatm and not (resn HOH+WAT+NA+CL+K+MG+ZN+SO4+PO4)"
        receptor_sel = "polymer"
    elif mode == "peptide":
        partner_sel  = f"chain {partner_chain}"
        receptor_sel = f"polymer and not chain {partner_chain}"
    elif mode == "protein":
        partner_sel  = f"chain {chain_b}"
        receptor_sel = f"chain {chain_a}"
    else:
        raise ValueError(f"unknown mode {mode}")

    pml = _write_pml(pdb_path, mode, label, interactions,
                     partner_selection=partner_sel,
                     receptor_selection=receptor_sel,
                     out_dir=out_dir, ligand_resname=ligand_resname,
                     resid_offset=resid_offset, img_size=img_size)

    print(f"[INFO] wrote PyMOL script: {pml}")
    if run and shutil.which("pymol"):
        print(f"[INFO] running: pymol -cq {pml}")
        try:
            r = subprocess.run(["pymol", "-cq", str(pml)],
                               capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                print(f"[WARN] pymol exit {r.returncode}\n{r.stderr[-800:]}")
            else:
                print("[INFO] PyMOL rendering done")
        except subprocess.TimeoutExpired:
            print("[WARN] PyMOL timed out")
        except Exception as e:
            print(f"[WARN] PyMOL run failed: {e}")
    elif run:
        print("[INFO] pymol not on PATH — only wrote .pml script")
    return pml

if __name__ == "__main__":
    run_cli()

