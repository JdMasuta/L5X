#!/usr/bin/env python3
"""
L5X Core Library

Core functions for extracting state machine logic from RSLogix L5X files
and generating Mermaid flowchart diagrams.

This module provides reusable library functions that can be imported
and used by CLI scripts, GUI applications, or other Python programs.

Author: Generated with Claude Code
"""

import l5x
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union, Callable, Any


def extract_state_number(tag_reference: str) -> Optional[int]:
    """
    Extract state number from a tag reference.

    Examples:
        '_A28_PH.ST[0].1' -> 1
        '_A28_PH.NST[0].14' -> 14

    Args:
        tag_reference: Tag reference string from ladder logic

    Returns:
        State number or None if not found
    """
    match = re.search(r'\.(\d+)$', tag_reference)
    if match:
        return int(match.group(1))
    return None


def get_state_name(prj: l5x.Project, tag_name: str, state_num: int) -> str:
    """
    Get the descriptive name for a state from tag bit description.

    Args:
        prj: L5X Project object
        tag_name: Name of the state tag (e.g., '_A28_PH')
        state_num: State number (bit number)

    Returns:
        State name string (fallback to "State {num}" if not found)
    """
    try:
        tag = prj.controller.tags[tag_name]
        st_0 = tag['ST'][0]
        bit = st_0[state_num]
        description = bit.description

        if description:
            lines = description.strip().split('\n')
            # First line is "State X", remaining lines are the name
            if len(lines) > 1:
                state_name = '\n'.join(lines[1:]).strip()
                return state_name

        return f"State {state_num}"

    except (KeyError, IndexError):
        # Return fallback name without printing (library function)
        return f"State {state_num}"


def find_state_logic_section(rll_content) -> Optional[int]:
    """
    Find the index of the STATE LOGIC section marker rung.

    Args:
        rll_content: RLLContent XML element containing rungs

    Returns:
        Index of STATE LOGIC marker rung or None if not found
    """
    for i, rung in enumerate(rll_content):
        comment = rung.find('Comment')
        if comment is not None:
            cdata = comment.find('CDATAContent')
            if cdata is not None and cdata.text and 'STATE LOGIC' in cdata.text:
                return i
    return None

# Here we create a new method of finding the state logic section
# We are looking for the rung that contains an OTU instruction called "S3_State_Logic"
def find_state_logic_section_by_otu(rll_content) -> Optional[int]:
    """
    Find the index of the STATE LOGIC section by looking for an OTU instruction.

    Args:
        rll_content: RLLContent XML element containing rungs

    Returns:
        Index of STATE LOGIC marker rung or None if not found
    """
    for i, rung in enumerate(rll_content):
        text = rung.find('Text')
        if text is not None:
            text_cdata = text.find('CDATAContent')
            if text_cdata is not None and text_cdata.text:
                logic = text_cdata.text.strip()
                otu_match = re.search(r'OTU\(([^)]+)\)', logic)
                if otu_match and 'S3_State_Logic' in otu_match.group(1):
                    return i
    return None


def parse_rung_logic(rung) -> Tuple[Optional[int], List[int]]:
    """
    Parse a rung to extract source state (XIC) and target states (OTL).

    Args:
        rung: Rung XML element

    Returns:
        Tuple of (source_state_number, [target_state_numbers])
        Returns (None, []) if rung is NOP or has no XIC
    """
    text = rung.find('Text')
    if text is None:
        return (None, [])

    text_cdata = text.find('CDATAContent')
    if text_cdata is None or not text_cdata.text:
        return (None, [])

    logic = text_cdata.text.strip()

    # Skip NOP() rungs
    if logic.startswith('NOP()'):
        return (None, [])

    # Extract source state from first XIC
    source_state = None
    xic_match = re.match(r'XIC\(([^)]+)\)', logic)
    if xic_match:
        xic_tag = xic_match.group(1)
        source_state = extract_state_number(xic_tag)

    # Extract target states from all OTL instructions
    target_states = []
    otl_matches = re.findall(r'OTL\(([^)]+)\)', logic)
    for otl_tag in otl_matches:
        target_state = extract_state_number(otl_tag)
        if target_state is not None:
            target_states.append(target_state)

    return (source_state, target_states)


def build_state_transitions(
    rll_content,
    start_index: int,
    end_marker: str = "FAULT"
) -> Dict[int, Set[int]]:
    """
    Build a map of state transitions from the STATE LOGIC section.

    Args:
        rll_content: RLLContent XML element
        start_index: Index where STATE LOGIC section starts
        end_marker: Comment text that marks end of STATE LOGIC section

    Returns:
        Dict mapping source_state -> set of target_states
    """
    state_transitions = {}
    rungs_list = list(rll_content)

    # Start from start_index + 2 to skip marker and cleanup rung
    for i in range(start_index + 2, len(rungs_list)):
        rung = rungs_list[i]

        # Check if we've reached the end of STATE LOGIC section
        comment = rung.find('Comment')
        if comment is not None:
            cdata = comment.find('CDATAContent')
            if cdata is not None and cdata.text and end_marker in cdata.text:
                break

        # Parse this rung
        source_state, target_states = parse_rung_logic(rung)

        if source_state is not None and target_states:
            # Initialize set for this source state if not exists
            if source_state not in state_transitions:
                state_transitions[source_state] = set()

            # Add all target states (set automatically handles duplicates)
            state_transitions[source_state].update(target_states)

    return state_transitions


def generate_mermaid_flowchart(
    title: str,
    state_transitions: Dict[int, Set[int]],
    state_names: Dict[int, str]
) -> str:
    """
    Generate Mermaid flowchart syntax from state transitions.

    Args:
        title: Diagram title
        state_transitions: Dict mapping source_state -> set of target_states
        state_names: Dict mapping state_number -> state_name

    Returns:
        Mermaid flowchart syntax as string
    """
    # Collect all unique state numbers
    all_states = set(state_transitions.keys())
    for targets in state_transitions.values():
        all_states.update(targets)

    graph_type = 'stateDiagram' if False else 'flowchart'  # Change to False to use flowchart

    config_lines = [
        '---',
        'title: {title}'.format(title=title),
        'config:',
        '  layout: elk' if graph_type == 'flowchart' else '  layout: dagre',
        # 'theme: base', # Use 'base' to allow full customization
        # 'themeVariables:',
        # '   primaryColor: #BBDEF0',
        # '   primaryTextColor: #000000',
        # '   primaryBorderColor: #7C7C7C',
        # '   lineColor: #F85A3E',
        # '   secondaryColor: #006100',
        # '   tertiaryColor: #fff',
        '---',
        ''
        'flowchart TB' if graph_type == 'flowchart' else 'stateDiagram-v2',
    ]

    if graph_type == 'flowchart':
        lines = config_lines

        # Generate node definitions
        # Format: S{state_num}[State {state_num}, {state_name}]
        for state_num in sorted(all_states):
            name = state_names.get(state_num, f"State {state_num}")
            # Clean up name for display (limit length, replace newlines)
            clean_name = name.replace('\n', ' - ')[:60]
            clean_name = clean_name.replace('(', '~')[:60]
            clean_name = clean_name.replace(')', '~')[:60]
            lines.append(f'    S{state_num}[State {state_num}, {clean_name}]')

        lines.append('')  # Blank line between nodes and edges

        # Generate edge definitions
        for source_state in sorted(state_transitions.keys()):
            for target_state in sorted(state_transitions[source_state]):
                # Draw double line for 1 to 1 transitions
                if (len(state_transitions[target_state]) == 0):
                    lines.append(f'    S{source_state} ==> S{target_state}')
                else:
                    lines.append(f'    S{source_state} --> S{target_state}')

    elif graph_type == 'stateDiagram':
        lines = config_lines

        # Generate node definitions
        # Format: State_{state_num} : State {state_num}, {state_name}
        for state_num in sorted(all_states):
            name = state_names.get(state_num, f"State {state_num}")
            clean_name = name.replace('\n', ' - ')[:60]
            lines.append(f'    S{state_num} : {state_num}. {clean_name}')

        lines.append('')  # Blank line between nodes and edges

        # Generate edge definitions
        for source_state in sorted(state_transitions.keys()):
            for target_state in sorted(state_transitions[source_state]):
                lines.append(f'    S{source_state} --> S{target_state}')

    return '\n'.join(lines)


def save_mermaid_diagram(mermaid_text: str, output_path: Union[str, Path]):
    """
    Save Mermaid diagram to a markdown file.

    Args:
        mermaid_text: Mermaid flowchart syntax
        output_path: Path to output markdown file
    """
    output_path = Path(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# State Logic Diagram\n\n')
        f.write('```mermaid\n')
        f.write(mermaid_text)
        f.write('\n```\n')


def render_mermaid_to_svg(
    markdown_file: Union[str, Path],
    output_svg_file: Optional[Union[str, Path]] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Render a Mermaid markdown file to SVG format.

    Args:
        markdown_file: Path to .md file containing Mermaid diagram
        output_svg_file: Path for output .svg file (auto-generated if None)
        progress_callback: Optional callback for progress messages

    Returns:
        Dictionary with keys:
            - success: bool - True if rendering succeeded
            - message: str - Success or error message
            - svg_file: str - Path to generated SVG file (empty on error)
            - error: Optional[str] - Error details if failed
    """
    # SVG rendering via mermaid-cli (Node.js) has been removed.
    # Diagrams are now rendered in the GUI viewer using mermaid.js loaded from CDN.
    markdown_path = Path(markdown_file)
    return {
        'success': False,
        'message': "CLI-based SVG rendering is not available. Use the diagram viewer in the GUI.",
        'svg_file': '',
        'mermaid_text': markdown_path.read_text(encoding='utf-8') if markdown_path.exists() else '',
        'error': None
    }


def generate_state_diagram(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    tag_name: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Generate state diagram from L5X file. Complete workflow in one function.

    This is the main entry point for library use. It coordinates all the
    individual functions to load an L5X file, extract state logic, generate
    a Mermaid diagram, and save it to a file.

    Args:
        input_file: Path to input .L5X file
        output_file: Path to output .md file
        tag_name: Optional state tag name (auto-detects if None)
        progress_callback: Optional callback for progress messages

    Returns:
        Dictionary with keys:
            - success: bool - True if diagram generated successfully
            - message: str - Success or error message
            - states: List[int] - State numbers found (empty on error)
            - transitions_count: int - Number of transitions (0 on error)
            - diagram_text: str - Mermaid syntax (empty on error)
            - error: Optional[str] - Error details if failed

    Raises:
        FileNotFoundError: If input file doesn't exist
        l5x.InvalidFile: If input file is not valid L5X
        ValueError: If no STATE LOGIC section found or tag detection fails
    """
    def progress(msg: str):
        """Helper to call progress callback if provided."""
        if progress_callback:
            progress_callback(msg)

    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        # Check input file exists
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Load L5X project
        progress(f"Loading L5X file: {input_path.name}")
        prj = l5x.Project(str(input_path))

        # Find the routine with STATE LOGIC section
        progress("Searching for STATE LOGIC section...")
        rll_content = None
        routine_name = None
        program_name = None
        state_logic_index = None

        for prog_name in prj.programs.names:
            program = prj.programs[prog_name]
            routines_elem = program.element.find('Routines')
            if routines_elem is not None:
                for routine in routines_elem:
                    temp_rll = routine.find('RLLContent')
                    if temp_rll is not None:
                        # Check if this routine has STATE LOGIC
                        state_logic_index = find_state_logic_section_by_otu(temp_rll)
                        if state_logic_index is not None:
                            rll_content = temp_rll
                            routine_name = routine.attrib.get('Name')
                            program_name = prog_name
                            break
                if rll_content is not None:
                    break

        if rll_content is None:
            raise ValueError("No STATE LOGIC section found in file")

        progress(f"Found STATE LOGIC in program: {program_name}, Routine: {routine_name}")

        # Auto-detect tag name if not provided; Should be the first tag on state_logic_index rung
        if tag_name is None:
            progress("Auto-detecting state tag...")
            # Try to find a StateLogic tag
            # Get the rung at state_logic_index
            state_logic_rung = rll_content[state_logic_index + 1]
            text = state_logic_rung.find('Text')
            if text is not None:
                text_cdata = text.find('CDATAContent')
                if text_cdata is not None and text_cdata.text:
                    logic = text_cdata.text.strip()
                    xic_match = re.match(r'XIC\(([^)]+)\)', logic)
                    progress("Logic: {logic} xic_match: {xic_match}".format(logic=logic, xic_match=xic_match))
                    if xic_match:
                        tag_reference = xic_match.group(1)
                        tag_name_candidate = tag_reference.split('.')[0]
                        try:
                            tag = prj.controller.tags[tag_name_candidate]
                            progress(f"Checking tag: {tag_name_candidate}")
                            # Tag should have a '.ST' member
                            if 'ST' in tag.names:
                                tag_name = tag_name_candidate
                                progress(f"Auto-detected state tag: {tag_name}")
                        except:
                            pass

        if tag_name is None:
            raise ValueError("Could not auto-detect state tag. Please specify tag_name parameter.")

        progress(f"Using state tag: {tag_name}")

        # Build state transitions map
        progress("Extracting state transitions...")
        state_transitions = build_state_transitions(rll_content, state_logic_index)

        if not state_transitions:
            progress("Warning: No state transitions found")

        progress(f"Found {len(state_transitions)} source states")

        # Get all state names
        progress("Retrieving state names...")
        all_states = set(state_transitions.keys())
        for targets in state_transitions.values():
            all_states.update(targets)

        state_names = {}
        for state_num in all_states:
            state_names[state_num] = get_state_name(prj, tag_name, state_num)

        # Generate Mermaid flowchart
        progress("Generating Mermaid flowchart...")
        mermaid_text = generate_mermaid_flowchart(routine_name, state_transitions, state_names)

        # Save to file
        progress(f"Saving diagram to: {output_path.name}")
        save_mermaid_diagram(mermaid_text, output_path)

        # Calculate statistics
        transitions_count = sum(len(targets) for targets in state_transitions.values())
        states_list = sorted(all_states)

        return {
            'success': True,
            'message': f"Diagram generated successfully",
            'states': states_list,
            'transitions_count': transitions_count,
            'diagram_text': mermaid_text,
            'error': None
        }

    except FileNotFoundError as e:
        return {
            'success': False,
            'message': str(e),
            'states': [],
            'transitions_count': 0,
            'diagram_text': '',
            'error': f"File not found: {str(e)}"
        }
    except l5x.InvalidFile as e:
        return {
            'success': False,
            'message': f"Invalid L5X file",
            'states': [],
            'transitions_count': 0,
            'diagram_text': '',
            'error': str(e)
        }
    except ValueError as e:
        return {
            'success': False,
            'message': str(e),
            'states': [],
            'transitions_count': 0,
            'diagram_text': '',
            'error': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Unexpected error: {str(e)}",
            'states': [],
            'transitions_count': 0,
            'diagram_text': '',
            'error': str(e)
        }


def main():
    """
    Main function for testing the library functions.

    This can be used for quick testing or as a starting point for a CLI script.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Generate state diagram from L5X file")
    parser.add_argument('input_file', help="Path to input .L5X file")
    parser.add_argument('output_file', help="Path to output .md file for Mermaid diagram")
    parser.add_argument('--tag', help="Optional state tag name (auto-detected if not provided)")
    args = parser.parse_args()

    result = generate_state_diagram(
        input_file=args.input_file,
        output_file=args.output_file,
        tag_name=args.tag,
        progress_callback=print
    )

    if result['success']:
        print(f"Diagram generated successfully with {len(result['states'])} states and {result['transitions_count']} transitions.")
    else:
        print(f"Failed to generate diagram: {result['message']}")
        if result['error']:
            print(f"Error details: {result['error']}")

if __name__ == "__main__":
    main()