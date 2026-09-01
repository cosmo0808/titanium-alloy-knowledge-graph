# script/entity_relation_extractor_db.py - Fixed version with proper imports
import sqlite3
import pandas as pd
import re
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path and import config
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from config.paths import DATABASE_PATH, PROCESSED_DATA_DIR

# Valid elements from periodic table
VALID_ELEMENTS = {
    "H","He","Li","Be","B","C","N","O","F","Ne",
    "Na","Mg","Al","Si","P","S","Cl","Ar",
    "K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn",
    "Ga","Ge","As","Se","Br","Kr",
    "Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd",
    "In","Sn","Sb","Te","I","Xe",
    "Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy",
    "Ho","Er","Tm","Yb","Lu","Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg",
    "Tl","Pb","Bi","Po","At","Rn",
    "Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm","Bk","Cf","Es","Fm",
    "Md","No","Lr","Rf","Db","Sg","Bh","Hs","Mt","Ds","Rg","Cn","Fl","Lv",
    "Ts","Og"
}

def load_table(db_path, table_name):
    """Load table from SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Failed to load table {table_name}: {e}")
        return pd.DataFrame()

def clean_alloy_name(name):
    """Clean alloy name by removing newlines, extra spaces and parenthetical notes."""
    if not name:
        return ""
    
    name = str(name).replace("\n", " ").strip()
    name = re.sub(r"\(.*?\)", "", name)  # Remove parenthetical content
    name = re.sub(r"\s+", " ", name)     # Merge multiple spaces
    return name

def truncate_label(name, length=40):
    """Truncate visualization labels for readability."""
    if not name:
        return ""
    name = str(name)
    return name if len(name) <= length else name[:length-3] + "..."

def extract_entities_from_materials(df):
    """Extract entities from Materials table."""
    nodes, edges = {}, []
    
    if df.empty:
        print("Materials table is empty")
        return nodes, edges
    
    # Try to find name column (could be in different positions/names)
    name_columns = ['name', 'material_name', 'alloy_name', 'title']
    name_col = None
    
    for col in name_columns:
        if col in df.columns:
            name_col = col
            break
    
    if name_col is None and len(df.columns) > 1:
        name_col = df.columns[1]  # Fallback to second column
    
    if name_col is None:
        print("Could not identify name column in Materials table")
        return nodes, edges
    
    print(f"Using column '{name_col}' as material name")
    
    for _, row in df.iterrows():
        try:
            material_name = row[name_col]
            if pd.isna(material_name) or not str(material_name).strip():
                continue
            
            clean_name = clean_alloy_name(material_name)
            if not clean_name:
                continue
            
            # Add alloy node
            if clean_name not in nodes:
                nodes[clean_name] = {"type": "alloy", "source": "database"}
            
            # Extract elements from alloy name using regex
            elements = re.findall(r"[A-Z][a-z]?", clean_name)
            for element in elements:
                if element in VALID_ELEMENTS:
                    if element not in nodes:
                        nodes[element] = {"type": "element", "source": "database"}
                    
                    # Add edge: alloy contains element
                    edge = [clean_name, element]
                    if edge not in edges:
                        edges.append(edge)
        
        except Exception as e:
            print(f"Error processing material row: {e}")
            continue
    
    return nodes, edges

def extract_properties(df, alloy_nodes):
    """Extract properties from Properties table."""
    nodes, edges = {}, []
    
    if df.empty:
        print("Properties table is empty")
        return nodes, edges
    
    # Try to identify columns
    material_col = None
    property_col = None
    value_col = None
    
    # Look for material reference column
    for col in ['material', 'material_id', 'material_name', 'alloy']:
        if col in df.columns:
            material_col = col
            break
    
    # Look for property columns
    for col in ['property', 'property_name', 'property_type']:
        if col in df.columns:
            property_col = col
            break
    
    # Look for value columns
    for col in ['value', 'metric_value', 'english_value', 'measurement']:
        if col in df.columns:
            value_col = col
            break
    
    if not all([material_col, property_col]):
        print(f"Could not identify required columns in Properties table")
        print(f"Available columns: {list(df.columns)}")
        return nodes, edges
    
    print(f"Using columns: material='{material_col}', property='{property_col}', value='{value_col}'")
    
    for _, row in df.iterrows():
        try:
            # Get material reference
            material_ref = row[material_col]
            if pd.isna(material_ref):
                continue
            
            # Handle different material reference types
            if material_col == 'material_id':
                # Look up material name by ID (simplified - assumes integer IDs map to alloy_nodes keys)
                material_name = None
                for alloy_name in alloy_nodes:
                    if str(material_ref) in alloy_name or alloy_name in str(material_ref):
                        material_name = alloy_name
                        break
            else:
                material_name = clean_alloy_name(str(material_ref))
            
            if not material_name or material_name not in alloy_nodes:
                continue
            
            # Get property info
            prop = str(row[property_col]).strip()
            if not prop or pd.isna(row[property_col]):
                continue
            
            # Get value if available
            value = ""
            if value_col and not pd.isna(row[value_col]):
                value = str(row[value_col]).strip()
            
            # Create property node
            if value:
                prop_node = f"{prop}: {value}".replace("\n", " ").strip()
            else:
                prop_node = prop
            
            prop_node = truncate_label(prop_node)
            
            if prop_node not in nodes:
                nodes[prop_node] = {"type": "property", "source": "database"}
            
            # Add edge: material has property
            edge = [material_name, prop_node]
            if edge not in edges:
                edges.append(edge)
        
        except Exception as e:
            print(f"Error processing property row: {e}")
            continue
    
    return nodes, edges

def main():
    """Main execution function."""
    print("Starting database entity extraction...")
    
    # Check if database exists
    if not DATABASE_PATH.exists():
        print(f"Database not found at: {DATABASE_PATH}")
        print("Creating empty knowledge graph...")
        
        # Create empty graph
        final_nodes = {}
        final_edges = []
    else:
        try:
            # Load Materials table
            print(f"Loading Materials table from: {DATABASE_PATH}")
            materials_df = load_table(DATABASE_PATH, "Materials")
            
            if materials_df.empty:
                print("Materials table is empty or could not be loaded")
                mat_nodes, mat_edges = {}, []
            else:
                mat_nodes, mat_edges = extract_entities_from_materials(materials_df)
                print(f"Extracted {len(mat_nodes)} nodes and {len(mat_edges)} edges from Materials")
            
            # Load Properties table
            try:
                print("Loading Properties table...")
                prop_df = load_table(DATABASE_PATH, "Properties")
                
                if prop_df.empty:
                    print("Properties table is empty or could not be loaded")
                    prop_nodes, prop_edges = {}, []
                else:
                    prop_nodes, prop_edges = extract_properties(prop_df, mat_nodes)
                    print(f"Extracted {len(prop_nodes)} property nodes and {len(prop_edges)} edges from Properties")
            
            except Exception as e:
                print(f"Error loading Properties table: {e}")
                prop_nodes, prop_edges = {}, []
            
            # Merge nodes and edges
            final_nodes = {**mat_nodes, **prop_nodes}
            final_edges = mat_edges + prop_edges
        
        except Exception as e:
            print(f"Error processing database: {e}")
            final_nodes = {}
            final_edges = []
    
    # Save results
    PROCESSED_DATA_DIR.mkdir(exist_ok=True)
    save_path = PROCESSED_DATA_DIR / "entities_relations_hg_db.json"
    
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"nodes": final_nodes, "edges": final_edges}, f, indent=2, ensure_ascii=False)
        
        print(f"Database extraction completed!")
        print(f"Results saved to: {save_path}")
        print(f"Total nodes: {len(final_nodes)}")
        print(f"Total edges: {len(final_edges)}")
        
        # Print node type distribution
        if final_nodes:
            node_types = {}
            for node_data in final_nodes.values():
                node_type = node_data.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
            
            print("Node type distribution:")
            for node_type, count in node_types.items():
                print(f"  {node_type}: {count}")
    
    except Exception as e:
        print(f"Error saving results: {e}")

if __name__ == "__main__":
    main()

