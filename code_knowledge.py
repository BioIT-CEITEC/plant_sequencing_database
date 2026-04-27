import os
import json
import glob
import tree_sitter_python
from tree_sitter import Language, Parser

def get_parser():
    PY_LANGUAGE = Language(tree_sitter_python.language())
    parser = Parser()
    parser.language = PY_LANGUAGE
    return parser

def build_structural_graph(project_root):
    parser = get_parser()
    
    graph = {
        "nodes": {},
        "edges": []
    }
    
    # Find all python files
    py_files = glob.glob(os.path.join(project_root, "**", "*.py"), recursive=True)
    
    for file_path in py_files:
        # Ignore venv
        if "bin/" in file_path or "lib/" in file_path or ".venv" in file_path:
            continue
            
        rel_path = os.path.relpath(file_path, project_root)
        
        with open(file_path, "r", encoding="utf-8") as f:
            code_str = f.read()
            
        tree = parser.parse(bytes(code_str, "utf8"))
        root_node = tree.root_node
        
        # Simple extraction logic for functions and classes
        # This can be made much more robust using queries
        
        for node in root_node.children:
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_name = code_str[name_node.start_byte:name_node.end_byte]
                    node_id = f"{rel_path}:{func_name}"
                    graph["nodes"][node_id] = {
                        "type": "function",
                        "name": func_name,
                        "file": rel_path,
                        "start_line": node.start_point[0],
                        "end_line": node.end_point[0]
                    }
                    
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = code_str[name_node.start_byte:name_node.end_byte]
                    node_id = f"{rel_path}:{class_name}"
                    graph["nodes"][node_id] = {
                        "type": "class",
                        "name": class_name,
                        "file": rel_path,
                        "start_line": node.start_point[0],
                        "end_line": node.end_point[0]
                    }
                    
                    # Add methods
                    body_node = node.child_by_field_name('body')
                    if body_node:
                        for child in body_node.children:
                            if child.type == 'function_definition':
                                method_name_node = child.child_by_field_name('name')
                                if method_name_node:
                                    method_name = code_str[method_name_node.start_byte:method_name_node.end_byte]
                                    method_id = f"{rel_path}:{class_name}.{method_name}"
                                    graph["nodes"][method_id] = {
                                        "type": "method",
                                        "name": method_name,
                                        "parent_class": class_name,
                                        "file": rel_path,
                                        "start_line": child.start_point[0],
                                        "end_line": child.end_point[0]
                                    }
                                    
            elif node.type == 'import_statement' or node.type == 'import_from_statement':
                # Simplified import recording
                graph["edges"].append({
                    "source": rel_path,
                    "target": "external_or_internal_module",
                    "type": "imports"
                })
                
    return graph

def save_graph(graph, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

def load_graph(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nodes": {}, "edges": []}

def query_graph(graph, node_id=None, node_type=None):
    results = []
    for nid, node_data in graph["nodes"].items():
        if node_id and nid != node_id:
            continue
        if node_type and node_data["type"] != node_type:
            continue
        results.append((nid, node_data))
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the code graph")
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    graph_path = os.path.join(project_root, "code_graph.json")
    
    if args.build:
        print("Building structural code graph...")
        graph = build_structural_graph(project_root)
        save_graph(graph, graph_path)
        print(f"Graph saved to {graph_path} with {len(graph['nodes'])} nodes.")
