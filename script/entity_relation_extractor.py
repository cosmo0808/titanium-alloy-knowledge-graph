# script/entity_relation_extractor.py - Final fixed version
import json
import re
from pathlib import Path
import pandas as pd
from datetime import datetime
import traceback
import sys
import subprocess
import logging
from typing import Optional, Dict, List, Any

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from config.paths import PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)

# Configuration
OUTPUT_FILE = PROCESSED_DATA_DIR / "entities_relations_hg.json"
MAX_FILES = 100

# Entity normalization mapping
ENTITY_WHITELIST = {
    "TI": "Ti", "NI": "Ni", "AL": "Al", "ZN": "Zn", "MO": "Mo", "ZR": "Zr",
    "H": "H", "F": "F", "P": "P", "SB": "Sb", "B": "B", "RC": "RC", "O": "O",
    "V": "V", "CR": "Cr", "MN": "Mn", "FE": "Fe", "CO": "Co", "CU": "Cu",
    "SN": "Sn", "NB": "Nb", "TA": "Ta", "W": "W"
}

# Valid element range for content percentage
VALUE_MIN = 0.0
VALUE_MAX = 50.0

# Valid elements from periodic table
VALID_ELEMENTS = {
    "Ti", "Al", "V", "Mo", "Nb", "Zr", "Sn", "Fe", "Cr", "Ni", "Cu", "Mn",
    "H", "F", "P", "Sb", "B", "O", "C", "N", "Si", "Mg", "Ca", "Co"
}

def clean_hypergraph(hypergraph: Dict[str, Any], valid_elements: set = None, 
                     alloy_cleanup: bool = True) -> Dict[str, Any]:
    """Clean and optimize hypergraph structure."""
    if valid_elements is None:
        valid_elements = VALID_ELEMENTS
    
    nodes_to_remove = []
    rename_map = {}
    
    # Clean invalid elements and normalize alloy names
    for node_id, node in hypergraph['nodes'].items():
        if node['type'] == 'element' and node_id not in valid_elements:
            nodes_to_remove.append(node_id)
        
        if alloy_cleanup and node['type'] == 'alloy':
            # Remove common suffixes that don't affect identity
            cleaned_name = re.sub(r'[-_]?COATED$', '', node_id, flags=re.IGNORECASE)
            cleaned_name = re.sub(r'[-_]?ALLOY$', '', cleaned_name, flags=re.IGNORECASE)
            if cleaned_name != node_id:
                rename_map[node_id] = cleaned_name
    
    # Apply renames
    for old_name, new_name in rename_map.items():
        hypergraph['nodes'][new_name] = hypergraph['nodes'][old_name]
        nodes_to_remove.append(old_name)
    
    # Remove invalid nodes
    for nid in nodes_to_remove:
        hypergraph['nodes'].pop(nid, None)
    
    # Clean edges and apply renames
    cleaned_edges = []
    for edge in hypergraph.get('edges', []):
        if isinstance(edge, dict):
            from_node = rename_map.get(edge['from'], edge['from'])
            to_node = rename_map.get(edge['to'], edge['to'])
            if from_node in hypergraph['nodes'] and to_node in hypergraph['nodes']:
                cleaned_edges.append({
                    'from': from_node, 
                    'to': to_node, 
                    'relation': edge['relation']
                })
        elif isinstance(edge, list) and len(edge) >= 2:
            from_node = rename_map.get(edge[0], edge[0])
            to_node = rename_map.get(edge[1], edge[1])
            if from_node in hypergraph['nodes'] and to_node in hypergraph['nodes']:
                cleaned_edges.append([from_node, to_node])
    
    hypergraph['edges'] = cleaned_edges
    
    # Remove isolated nodes
    connected_nodes = set()
    for edge in hypergraph['edges']:
        if isinstance(edge, dict):
            connected_nodes.add(edge['from'])
            connected_nodes.add(edge['to'])
        elif isinstance(edge, list) and len(edge) >= 2:
            connected_nodes.add(edge[0])
            connected_nodes.add(edge[1])
    
    isolated_nodes = set(hypergraph['nodes'].keys()) - connected_nodes
    for nid in isolated_nodes:
        hypergraph['nodes'].pop(nid, None)
    
    logger.info(f"Hypergraph cleaned! Remaining nodes: {len(hypergraph['nodes'])}, edges: {len(hypergraph['edges'])}")
    return hypergraph


class SimpleMultimodalParser:
    """Simple rule-based parser as fallback when LLM is not available."""
    
    def __init__(self):
        # Element patterns for extraction
        self.element_patterns = [
            r'([A-Z][a-z]?)(?:\s*[:\-]\s*)?([\d\.]+)(?:\s*[%wt])?',  # Ti: 6.0%
            r'([A-Z][a-z]?)\s*content\s*(?:of\s*)?([\d\.]+)(?:\s*[%wt])?',  # Al content 4.0%
            r'([\d\.]+)(?:\s*[%wt])?\s*([A-Z][a-z]?)',  # 6.0% Ti
        ]
        
        # Alloy patterns
        self.alloy_patterns = [
            r'Ti[-â€“][\d\w\-â€“]+(?:\s*[Aa]lloy)?',
            r'TC\d+', r'TA\d+', r'TB\d+',
            r'Ti\d+Al\d+V?',
            r'Grade\s*\d+',
        ]
    
    def parse_image(self, img_path: str) -> str:
        """Parse image - placeholder implementation."""
        logger.info(f"Image parsing placeholder for: {img_path}")
        return f"Placeholder: extracted elements from {Path(img_path).name}"
    
    def parse_formula(self, formula_latex: str) -> str:
        """Parse LaTeX formula - extract element symbols."""
        logger.info(f"Formula parsing: {formula_latex[:50]}...")
        
        # Extract element symbols from LaTeX
        elements = re.findall(r'([A-Z][a-z]?)(?:_?\{?(\d+\.?\d*)\}?)?', formula_latex)
        
        results = []
        for element, ratio in elements:
            if element in VALID_ELEMENTS:
                if ratio:
                    results.append(f"{element}: {ratio}")
                else:
                    results.append(element)
        
        return " ".join(results)


class QwenParser:
    """Enhanced parser with Ollama integration and fallback."""
    
    def __init__(self, model_name: str = "qwen2.5vl:3b"):
        self.model_name = model_name
        self.fallback_parser = SimpleMultimodalParser()
        self.available = self._check_ollama_availability()
    
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is available."""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _call_llm(self, prompt: str) -> str:
        """Call Ollama LLM with fallback to simple parser."""
        if not self.available:
            logger.warning("Ollama not available, using fallback parser")
            return "Fallback parser - no LLM available"
        
        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name],
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"LLM call failed: {result.stderr.strip()}")
                return f"LLM call failed: {prompt[:50]}..."
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            logger.warning("LLM call timed out")
            return f"LLM timeout: {prompt[:50]}..."
        except Exception as e:
            logger.warning(f"LLM call exception: {e}")
            return f"LLM error: {prompt[:50]}..."
    
    def parse_image(self, img_path: str) -> str:
        """Parse image with LLM or fallback."""
        if not self.available:
            return self.fallback_parser.parse_image(img_path)
        
        prompt = f"""
        Extract all alloy materials, chemical elements and their contents from this materials image.
        Format requirements:
        Element: Content%
        Image path: {img_path}
        """
        return self._call_llm(prompt)
    
    def parse_formula(self, formula_latex: str) -> str:
        """Parse LaTeX formula with LLM or fallback."""
        if not self.available:
            return self.fallback_parser.parse_formula(formula_latex)
        
        prompt = f"""
        Parse the following LaTeX chemical formula and extract elements with their ratios/contents:
        {formula_latex}
        
        Format: Element: Ratio/Content
        """
        return self._call_llm(prompt)


class RuleBasedExtractorHG:
    """Enhanced rule-based entity and relation extractor for hypergraph construction."""
    
    def __init__(self, processed_dir: Path):
        self.processed_dir = Path(processed_dir)
        self.entities_relations = []
        self.hypergraph = {'nodes': {}, 'edges': []}
        self.parser = QwenParser()
        
        # Enhanced patterns for alloy domain
        self.alloy_patterns = [
            r'Ti[-â€“][\d\w\-â€“]+(?:\s*[Aa]lloy)?',
            r'TC\d+', r'TA\d+', r'TB\d+', r'TG\d+',
            r'Ti\d+Al\d+V?\d*',
            r'Grade\s*\d+',
            r'Ti[-â€“]?6Al[-â€“]?4V',
            r'Ti[-â€“]?6[-â€“]?4',
            r'TNTZ', r'TNTZ[-â€“]?\d*'
        ]
        
        self.element_patterns = [
            r'([A-Z][a-z]?)(?:\s*[:\-]\s*)?([\d\.]+)(?:\s*[%wt])?',
            r'([A-Z][a-z]?)\s*content\s*(?:of\s*)?([\d\.]+)(?:\s*[%wt])?',
            r'([\d\.]+)(?:\s*[%wt])?\s*([A-Z][a-z]?)',
            r'([A-Z][a-z]?)(?:\s*[:=]\s*)([\d\.]+)',
        ]
        
        self.property_patterns = [
            r'(tensile\s+strength|yield\s+strength|hardness|modulus)\s*[:\-]?\s*([\d\.]+)\s*([A-Za-z/]+)?',
            r'(strength|hardness|modulus|toughness)\s*[:\-]?\s*([\d\.]+)',
            r'(mechanical\s+properties?|thermal\s+properties?)',
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove excessive whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\u2000-\u206F\u2E00-\u2E7F]+', '', text)
        text = re.sub(r'[^\w\s\-\.%:=()]', ' ', text)
        
        return text.strip()
    
    def normalize_entity(self, entity: str) -> Optional[str]:
        """Normalize entity names."""
        if not entity:
            return None
        
        # Character replacements for common OCR errors
        entity = entity.replace('l', '1').replace('I', '1')
        entity = entity.replace('O', '0').replace('o', '0')
        entity = entity.replace('S', '5')
        
        # Remove whitespace and normalize case
        entity = re.sub(r'\s+', '', entity)
        entity = entity.upper().strip()
        
        # Apply whitelist mapping
        return ENTITY_WHITELIST.get(entity, entity)
    
    def parse_value(self, val: Any) -> Optional[str]:
        """Parse and validate numerical values."""
        if val is None:
            return None
        
        val_str = str(val).strip().replace('%', '').replace('wt', '')
        
        try:
            f = float(val_str)
            
            # Convert fractions to percentages
            if 0 <= f <= 1:
                f = f * 100
            
            # Validate range
            if VALUE_MIN <= f <= VALUE_MAX:
                return f"{f:.2f}%"
        except (ValueError, TypeError):
            pass
        
        return None
    
    def extract_from_text(self, pdf_data: Dict[str, Any]) -> None:
        """Extract entities and relations from text content."""
        filename = pdf_data.get('filename', 'unknown')
        
        for page, content in pdf_data.get('text', {}).items():
            if not content:
                continue
            
            text = self.clean_text(content)
            self._extract_alloys_from_text(text, filename, 'text')
            self._extract_elements_from_text(text, filename, 'text')
            self._extract_properties_from_text(text, filename, 'text')
    
    def _extract_alloys_from_text(self, text: str, filename: str, source: str) -> None:
        """Extract alloy names from text."""
        for pattern in self.alloy_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self.normalize_entity(match)
                if normalized:
                    self.entities_relations.append({
                        'pdf_file': filename,
                        'entity': normalized,
                        'attribute': 'alloy_type',
                        'value': None,
                        'source': source
                    })
    
    def _extract_elements_from_text(self, text: str, filename: str, source: str) -> None:
        """Extract elements and their contents from text."""
        for pattern in self.element_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    element, value = match
                    element_norm = self.normalize_entity(element)
                    value_parsed = self.parse_value(value)
                    
                    if element_norm in VALID_ELEMENTS and value_parsed:
                        self.entities_relations.append({
                            'pdf_file': filename,
                            'entity': element_norm,
                            'attribute': 'content',
                            'value': [value_parsed],
                            'source': source
                        })
    
    def _extract_properties_from_text(self, text: str, filename: str, source: str) -> None:
        """Extract material properties from text."""
        for pattern in self.property_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    prop_name = match[0].strip()
                    prop_value = match[1] if len(match) > 1 else ""
                    prop_unit = match[2] if len(match) > 2 else ""
                    
                    property_full = f"{prop_name}: {prop_value} {prop_unit}".strip()
                    
                    self.entities_relations.append({
                        'pdf_file': filename,
                        'entity': property_full,
                        'attribute': 'property',
                        'value': None,
                        'source': source
                    })
    
    def extract_from_tables(self, pdf_data: Dict[str, Any]) -> None:
        """Extract entities from table data."""
        filename = pdf_data.get('filename', 'unknown')
        
        for table in pdf_data.get('tables', []):
            try:
                csv_file = table.get('csv_file')
                
                # 内联表示（仅 page/table_num/rows/columns 元数据）无 csv_file，
                # 且不含可提取的单元格内容，保持兼容跳过，避免 KeyError 中断图谱构建
                if not csv_file:
                    logger.debug(
                        f"Skipping inline-only table (page={table.get('page')}, "
                        f"table_num={table.get('table_num')}, rows={table.get('rows')}, "
                        f"columns={table.get('columns')}): no csv_file"
                    )
                    continue
                
                csv_path = self.processed_dir / csv_file
                
                if not csv_path.exists():
                    continue
                
                df = pd.read_csv(csv_path)
                
                # Find element and value columns
                element_cols = [c for c in df.columns 
                              if any(k in str(c).lower() 
                                   for k in ['element', 'component', 'å…ƒç´ '])]
                value_cols = [c for c in df.columns 
                            if any(k in str(c).lower() 
                                 for k in ['content', 'percent', 'value', 'å«é‡', '%'])]
                
                # Extract element-value pairs
                for _, row in df.iterrows():
                    for e_col in element_cols:
                        element = row.get(e_col)
                        if pd.isna(element):
                            continue
                        
                        for v_col in value_cols:
                            value = row.get(v_col)
                            if pd.isna(value):
                                continue
                            
                            element_norm = self.normalize_entity(str(element))
                            value_parsed = self.parse_value(value)
                            
                            if element_norm in VALID_ELEMENTS and value_parsed:
                                self.entities_relations.append({
                                    'pdf_file': filename,
                                    'entity': element_norm,
                                    'attribute': 'content',
                                    'value': [value_parsed],
                                    'source': 'table'
                                })
                                
            except Exception as e:
                logger.warning(f"Failed to process table {csv_path if 'csv_path' in locals() else table}: {e}")
    
    def extract_from_images(self, pdf_data: Dict[str, Any]) -> None:
        """Extract entities from images using multimodal parser."""
        filename = pdf_data.get('filename', 'unknown')
        
        for img in pdf_data.get('images', []):
            img_file = img.get('img_file')
            if not img_file:
                continue
            
            logger.info(f"Processing image: {img_file}")
            
            try:
                text = self.parser.parse_image(img_file)
                if text and 'Placeholder' not in text:
                    self._extract_elements_from_text(text, filename, 'image')
                    self._extract_alloys_from_text(text, filename, 'image')
            except Exception as e:
                logger.warning(f"Failed to process image {img_file}: {e}")
    
    def extract_from_formulas(self, pdf_data: Dict[str, Any]) -> None:
        """Extract entities from chemical formulas."""
        filename = pdf_data.get('filename', 'unknown')
        
        for formula in pdf_data.get('formulas', []):
            latex = formula.get('latex')
            if not latex:
                continue
            
            logger.info(f"Processing formula: {latex[:30]}...")
            
            try:
                text = self.parser.parse_formula(latex)
                if text and 'Placeholder' not in text:
                    self._extract_elements_from_text(text, filename, 'formula')
            except Exception as e:
                logger.warning(f"Failed to process formula {latex[:30]}: {e}")
    
    def deduplicate_entities(self) -> None:
        """Remove duplicate entities and merge values."""
        merged = {}
        
        for item in self.entities_relations:
            # Create unique key
            key = (
                item['pdf_file'], 
                self.normalize_entity(item['entity']), 
                item['attribute'], 
                item['source']
            )
            
            # Get values list
            val_list = item['value'] if isinstance(item['value'], list) else (
                [item['value']] if item['value'] else []
            )
            
            # Merge or create entry
            if key in merged:
                merged[key].extend(val_list)
            else:
                merged[key] = val_list
        
        # Rebuild entities_relations
        self.entities_relations = []
        for k, v_list in merged.items():
            pdf_file, entity, attribute, source = k
            
            # Skip empty entities
            if not entity:
                continue
            
            # Remove duplicates from values
            v_list = list(dict.fromkeys([v for v in v_list if v is not None]))
            
            self.entities_relations.append({
                'pdf_file': pdf_file,
                'entity': entity,
                'attribute': attribute,
                'value': v_list if v_list else None,
                'source': source
            })
    
    def build_hypergraph(self) -> None:
        """Build hypergraph structure from extracted entities and relations."""
        for item in self.entities_relations:
            entity = item['entity']
            attribute = item['attribute']
            
            # Add entity node
            if entity not in self.hypergraph['nodes']:
                entity_type = self._determine_entity_type(entity, attribute)
                self.hypergraph['nodes'][entity] = {
                    'type': entity_type,
                    'pdf_file': item['pdf_file'],
                    'source': item['source']
                }
            
            # Add value nodes and edges
            if attribute and item['value']:
                for val in item['value']:
                    val_node = f"{entity}_{val}_{attribute}"
                    
                    if val_node not in self.hypergraph['nodes']:
                        self.hypergraph['nodes'][val_node] = {
                            'type': 'value',
                            'value': val,
                            'attribute': attribute,
                            'pdf_file': item['pdf_file'],
                            'source': item['source']
                        }
                    
                    # Add edge
                    self.hypergraph['edges'].append([entity, val_node])
    
    def _determine_entity_type(self, entity: str, attribute: str) -> str:
        """Determine the type of an entity based on its properties."""
        if entity in VALID_ELEMENTS:
            return 'element'
        elif attribute == 'alloy_type':
            return 'alloy'
        elif attribute == 'property':
            return 'property'
        elif any(pattern in entity.lower() for pattern in ['ti-', 'tc', 'ta', 'grade']):
            return 'alloy'
        else:
            return 'material'
    
    def run(self) -> None:
        """Execute the complete extraction pipeline."""
        logger.info("Starting entity and relation extraction...")
        
        # Find processed JSON files
        json_files = list(self.processed_dir.glob("*_processed.json"))[:MAX_FILES]
        logger.info(f"Found {len(json_files)} processed files")
        
        for json_file in json_files:
            try:
                logger.info(f"Processing: {json_file.name}")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    pdf_data = json.load(f)
                
                # Extract from different modalities
                self.extract_from_text(pdf_data)
                self.extract_from_tables(pdf_data)
                self.extract_from_images(pdf_data)
                self.extract_from_formulas(pdf_data)
                
            except Exception as e:
                logger.error(f"Failed to process {json_file.name}: {e}")
                logger.error(traceback.format_exc())
        
        # Post-processing
        logger.info("Deduplicating entities...")
        self.deduplicate_entities()
        
        logger.info("Building hypergraph...")
        self.build_hypergraph()
        
        logger.info("Cleaning hypergraph...")
        self.hypergraph = clean_hypergraph(self.hypergraph)
        
        # Save results
        OUTPUT_FILE.parent.mkdir(exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.hypergraph, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Extraction completed! Hypergraph saved to {OUTPUT_FILE}")
        logger.info(f"Final stats: {len(self.hypergraph['nodes'])} nodes, {len(self.hypergraph['edges'])} edges")


# Main execution
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    extractor = RuleBasedExtractorHG(PROCESSED_DATA_DIR)
    extractor.run()

