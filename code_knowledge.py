"""
code_knowledge.py — Structural code graph for CODEBASE navigation only.

PURPOSE:
  - Map functions, classes, methods, and import relationships
  - Support dependency understanding and code navigation

NOT FOR:
  - Document retrieval (use retrieval_engine.py → ChromaDB)
  - Metadata extraction (use extract_from_response() in app.py)
  - User-facing queries (use /api/chat endpoint)

This module has NO runtime connection to the document pipeline.
"""
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
            
        code_bytes = bytes(code_str, "utf8")
        tree = parser.parse(code_bytes)
        root_node = tree.root_node
        
        # Simple extraction logic for functions and classes
        # This can be made much more robust using queries
        
        for node in root_node.children:
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf8")
                    func_name = func_name.split('(')[0].strip()
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
                    class_name = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf8")
                    class_name = class_name.split('(')[0].strip()
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
                                    method_name = code_bytes[method_name_node.start_byte:method_name_node.end_byte].decode("utf8")
                                    method_name = method_name.split('(')[0].strip()
                                    method_id = f"{rel_path}:{class_name}.{method_name}"
                                    graph["nodes"][method_id] = {
                                        "type": "method",
                                        "name": method_name,
                                        "parent_class": class_name,
                                        "file": rel_path,
                                        "start_line": child.start_point[0],
                                        "end_line": child.end_point[0]
                                    }
                                    
            elif node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = code_bytes[child.start_byte:child.end_byte].decode("utf8")
                        graph["edges"].append({
                            "source": rel_path,
                            "target": module_name,
                            "type": "imports"
                        })
            elif node.type == 'import_from_statement':
                module_node = node.child_by_field_name('module_name')
                if module_node:
                    module_name = code_bytes[module_node.start_byte:module_node.end_byte].decode("utf8")
                    graph["edges"].append({
                        "source": rel_path,
                        "target": module_name,
                        "type": "imports_from"
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
