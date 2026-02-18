#!/usr/bin/env python3
"""
L5X State Logic Diagram Generator

Extracts state machine logic from RSLogix L5X files and generates Mermaid flowchart diagrams.

Usage:
    python l5x_state_diagram.py input.L5X [-o output.md] [-t TAG_NAME]

Author: Generated with Claude Code
"""

import l5x
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


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

    except (KeyError, IndexError, Exception) as e:
        print(f"Warning: Could not get name for state {state_num}: {e}", file=sys.stderr)
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
        state_transitions: Dict mapping source_state -> set of target_states
        state_names: Dict mapping state_number -> state_name

    Returns:
        Mermaid flowchart syntax as string
    """
    # Collect all unique state numbers
    all_states = set(state_transitions.keys())
    for targets in state_transitions.values():
        all_states.update(targets)

    graph_type = 'stateDiagram' if True else 'flowchart'  # Change to False to use flowchart

    if graph_type == 'flowchart':
        lines = ['---',
                'title: {title}'.format(title=title),
                'config:',
                '  layout: elk',
                '---', '',
                'flowchart TB', '']

        # Generate node definitions
        # Format: S{state_num}[State {state_num}, {state_name}]
        for state_num in sorted(all_states):
            name = state_names.get(state_num, f"State {state_num}")
            # Clean up name for display (limit length, replace newlines)
            clean_name = name.replace('\n', ' - ')[:60]
            clean_name = clean_name.replace('(', '<')[:60]
            clean_name = clean_name.replace(')', '>')[:60]
            lines.append(f'    S{state_num}[State {state_num}, {clean_name}]')

        lines.append('')  # Blank line between nodes and edges

        # Generate edge definitions
        for source_state in sorted(state_transitions.keys()):
            for target_state in sorted(state_transitions[source_state]):
                # Draw double line for 1 to 1 transitions
                if (len(state_transitions[target_state]) == 1):
                    lines.append(f'    S{source_state} ==> S{target_state}')
                else:
                    lines.append(f'    S{source_state} --> S{target_state}')

    elif graph_type == 'stateDiagram':
        lines = ['---',
                'title: {title}'.format(title=title),
                'config:',
                '  layout: elk',
                '---', '',
                'stateDiagram-v2',
                '    direction TB', '']
        
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


def save_mermaid_diagram(mermaid_text: str, output_path: Path):
    """
    Save Mermaid diagram to a markdown file.

    Args:
        mermaid_text: Mermaid flowchart syntax
        output_path: Path to output markdown file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# State Logic Diagram\n\n')
        f.write('```mermaid\n')
        f.write(mermaid_text)
        f.write('\n```\n')


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate Mermaid flowchart from L5X State Logic section',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s input.L5X
  %(prog)s input.L5X -o diagram.md
  %(prog)s input.L5X -t _A28_PH -o output.md
        '''
    )
    parser.add_argument('input_file', help='Path to input .L5X file')
    parser.add_argument(
        '-o', '--output',
        help='Output markdown file (default: <input>_state_diagram.md)'
    )
    parser.add_argument(
        '-t', '--tag',
        help='State tag name (default: auto-detect first StateLogic tag)'
    )

    args = parser.parse_args()

    # Determine input and output paths
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(f'{input_path.stem}_state_diagram.md')

    try:
        # Load L5X project
        print(f"Loading L5X file: {input_path}")
        prj = l5x.Project(str(input_path))

        # Find the routine with STATE LOGIC section
        print("Searching for STATE LOGIC section...")
        rll_content = None
        routine_name = None

        for program_name in prj.programs.names:
            program = prj.programs[program_name]
            routines_elem = program.element.find('Routines')
            if routines_elem is not None:
                for routine in routines_elem:
                    temp_rll = routine.find('RLLContent')
                    if temp_rll is not None:
                        # Check if this routine has STATE LOGIC
                        if find_state_logic_section(temp_rll) is not None:
                            rll_content = temp_rll
                            routine_name = routine.attrib.get('Name')
                            break
                if rll_content is not None:
                    break

        if rll_content is None:
            print("Error: No STATE LOGIC section found in file", file=sys.stderr)
            sys.exit(1)

        print(f"Found STATE LOGIC in program: {program_name}, Routine: {routine_name}")

        # Find STATE LOGIC section
        state_logic_index = find_state_logic_section(rll_content)
        print(f"STATE LOGIC section starts at rung index: {state_logic_index}")

        # Auto-detect tag name if not provided
        tag_name = args.tag
        print(f"Using state tag: {tag_name if tag_name else 'auto-detecting...'}")
        if tag_name is None:
            # Try to find a StateLogic tag
            for tag_name_candidate in prj.controller.tags.names:
                try:
                    tag = prj.controller.tags[tag_name_candidate]
                    print(f"Checking tag '{tag_name_candidate}' for StateLogic...")
                    if tag.data_type == 'StateLogic':
                        tag_name = tag_name_candidate
                        print(f"Auto-detected state tag: {tag_name}")
                        break
                except:
                    continue

        if tag_name is None:
            print("Error: Could not auto-detect state tag. Please specify with -t option", file=sys.stderr)
            sys.exit(1)

        # Build state transitions map
        print("Extracting state transitions...")
        state_transitions = build_state_transitions(rll_content, state_logic_index)
        print(f"State transitions: {state_transitions}")

        if not state_transitions:
            print("Warning: No state transitions found", file=sys.stderr)
        else:
            print(f"Found {len(state_transitions)} source states")

        # Get all state names
        print("Retrieving state names...")
        all_states = set(state_transitions.keys())
        for targets in state_transitions.values():
            all_states.update(targets)
            
        state_names = {}
        for state_num in all_states:
            state_names[state_num] = get_state_name(prj, tag_name, state_num)

        # Generate Mermaid flowchart
        print("Generating Mermaid flowchart...")
        mermaid_text = generate_mermaid_flowchart(routine_name,state_transitions, state_names)

        # Save to file
        save_mermaid_diagram(mermaid_text, output_path)

        print(f"\nSuccess! Diagram saved to: {output_path}")
        print(f"States found: {sorted(all_states)}")
        print(f"Total transitions: {sum(len(targets) for targets in state_transitions.values())}")

    except l5x.InvalidFile as e:
        print(f"Error: Invalid L5X file - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
