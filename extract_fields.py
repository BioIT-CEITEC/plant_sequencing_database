"""
Extract structured field information from ERC000022.xml
Traverses the hierarchy: FIELD_GROUP > FIELD > NAME, FIELD_TYPE, Text_values
"""

import xml.etree.ElementTree as ET
import json
from pathlib import Path


def extract_text_values_from_field_type(field_type_elem):
    """
    Extract text values from FIELD_TYPE element.
    Handles both TEXT_CHOICE_FIELD (with multiple values) and TEXT_FIELD.
    
    Args:
        field_type_elem: The FIELD_TYPE XML element
        
    Returns:
        List of text values or None if empty
    """
    text_values = []
    
    # Check for TEXT_CHOICE_FIELD with TEXT_VALUE entries
    text_choice = field_type_elem.find('TEXT_CHOICE_FIELD')
    if text_choice is not None:
        for text_value_elem in text_choice.findall('TEXT_VALUE'):
            value_elem = text_value_elem.find('VALUE')
            if value_elem is not None and value_elem.text:
                text_values.append(value_elem.text)
    
    # Return the list if not empty, otherwise None
    return text_values if text_values else None


def extract_field_data(field_elem):
    """
    Extract data from a single FIELD element.
    
    Args:
        field_elem: The FIELD XML element
        
    Returns:
        Dictionary containing name, field_type_element, and text_values
    """
    # Extract Name
    name_elem = field_elem.find('NAME')
    name = name_elem.text if name_elem is not None else None
    
    # Extract FIELD_TYPE element information
    field_type_elem = field_elem.find('FIELD_TYPE')
    field_type_info = None
    text_values = None
    
    if field_type_elem is not None:
        # Determine the type of FIELD_TYPE
        if field_type_elem.find('TEXT_CHOICE_FIELD') is not None:
            field_type_info = "TEXT_CHOICE_FIELD"
        elif field_type_elem.find('TEXT_FIELD') is not None:
            field_type_info = "TEXT_FIELD"
        else:
            field_type_info = "UNKNOWN"
        
        # Extract text values
        text_values = extract_text_values_from_field_type(field_type_elem)
    
    return {
        "name": name,
        "field_type": field_type_info,
        "text_values": text_values
    }


def extract_field_groups_data(xml_file_path):
    """
    Extract all field group and field data from XML.
    
    Args:
        xml_file_path: Path to the XML file
        
    Returns:
        List of dictionaries containing field groups and their fields
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # Navigate to DESCRIPTOR
    descriptor = root.find('.//DESCRIPTOR')
    if descriptor is None:
        raise ValueError("DESCRIPTOR element not found in XML")
    
    field_groups = []
    
    # Iterate through all FIELD_GROUP elements
    for field_group_elem in descriptor.findall('FIELD_GROUP'):
        # Extract FIELD_GROUP name
        group_name_elem = field_group_elem.find('NAME')
        group_name = group_name_elem.text if group_name_elem is not None else None
        
        # Extract restriction type attribute
        restriction_type = field_group_elem.get('restrictionType', None)
        
        # Extract all fields within this group
        fields = []
        for field_elem in field_group_elem.findall('FIELD'):
            field_data = extract_field_data(field_elem)
            fields.append(field_data)
        
        field_groups.append({
            "group_name": group_name,
            "restriction_type": restriction_type,
            "fields": fields
        })
    
    return field_groups


def main():
    """Main function to extract and save to JSON."""
    xml_file_path = Path(__file__).parent / "meta_data" / "ERC000022.xml"
    output_file_path = Path(__file__).parent / "extracted_fields.json"
    
    try:
        # Extract data
        print(f"Extracting data from: {xml_file_path}")
        field_groups_data = extract_field_groups_data(str(xml_file_path))
        
        # Create output structure
        output = {
            "source_file": str(xml_file_path),
            "total_field_groups": len(field_groups_data),
            "field_groups": field_groups_data
        }
        
        # Save to JSON
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n✓ Extraction complete!")
        print(f"✓ Output saved to: {output_file_path}")
        print(f"\nSummary:")
        print(f"  Total Field Groups: {len(field_groups_data)}")
        
        total_fields = sum(len(fg['fields']) for fg in field_groups_data)
        print(f"  Total Fields: {total_fields}")
        
        # Count fields with text values
        fields_with_values = 0
        for fg in field_groups_data:
            for field in fg['fields']:
                if field['text_values'] is not None:
                    fields_with_values += 1
        
        print(f"  Fields with Text Values: {fields_with_values}")
        print(f"  Fields without Text Values: {total_fields - fields_with_values}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
