import yaml
import os
import unicodedata
import re
import argparse
import sys
from difflib import get_close_matches
from typing import Dict, List, Set, Tuple, Optional, Any, Union

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class SpecProcessValidator:
    """
    A tool for validating and normalizing process and spec names against a reference.

    This class provides functionality to:
    1. Check if a process or spec exists in the reference
    2. Normalize process and spec names (remove whitespace, standardize format)
    3. Suggest similar processes or specs using fuzzy matching
    4. Add new processes or specs to the reference
    """

    def __init__(self, yaml_path: str = None):
        """
        Initialize the validator with a reference YAML file.

        Args:
            yaml_path: Path to the vendor_options.yaml file. If None, will look in default locations.
        """
        if yaml_path is None:
            # Try to find the yaml file in common locations
            possible_paths = [
                'vendor_options.yaml',
                'docs/OS/vendor_options.yaml',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'OS', 'vendor_options.yaml')
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    yaml_path = path
                    break

            if yaml_path is None:
                raise FileNotFoundError("Could not find vendor_options.yaml in default locations")

        # Load the reference data
        with open(yaml_path, 'r', encoding='utf-8') as f:
            self.ref = yaml.safe_load(f)

        self.yaml_path = yaml_path

        # Extract processes and specs
        self.processes = {p['name'] for v in self.ref['vendors'] for p in v.get('processes', [])}
        self.specs = {s['number'] for v in self.ref['vendors']
                      for p in v.get('processes', [])
                      for s in (p.get('specs') or [])}

        # Build normalized maps
        self._build_normalized_maps()

    def _build_normalized_maps(self):
        """Build maps from normalized text to original text."""
        self.norm_to_proc = {self.normalize(p): p for p in self.processes}
        self.norm_to_spec = {self.normalize(s): s for s in self.specs}

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text by removing extra whitespace, standardizing dashes, etc.

        Args:
            text: The text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to string if not already
        text = str(text)

        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)

        # Replace various dash characters with standard dash
        text = text.replace('—', '-').replace('–', '-').replace('�', '-')

        # Remove trailing commas and periods
        text = text.rstrip(',.;:')

        # Replace multiple spaces with a single space
        text = ' '.join(text.split())

        # Remove "per" and surrounding whitespace if it exists
        text = re.sub(r'\s+per\s+', ' ', text, flags=re.IGNORECASE)

        # Strip whitespace and convert to lowercase
        return text.strip().lower()

    def check_process(self, process: str) -> Tuple[bool, str, List[str]]:
        """
        Check if a process exists in the reference.

        Args:
            process: The process name to check

        Returns:
            Tuple containing:
                - Whether the process exists (after normalization)
                - The normalized process name
                - List of suggested matches if not found
        """
        norm_process = self.normalize(process)

        # Check for exact match after normalization
        if norm_process in self.norm_to_proc:
            return True, self.norm_to_proc[norm_process], []

        # If no exact match, get fuzzy matches
        matches = get_close_matches(norm_process, self.norm_to_proc.keys(), n=3, cutoff=0.6)
        suggestions = [self.norm_to_proc[m] for m in matches]

        return False, norm_process, suggestions

    def check_spec(self, spec: str) -> Tuple[bool, str, List[str]]:
        """
        Check if a spec exists in the reference.

        Args:
            spec: The spec name to check

        Returns:
            Tuple containing:
                - Whether the spec exists (after normalization)
                - The normalized spec name
                - List of suggested matches if not found
        """
        norm_spec = self.normalize(spec)

        # Check for exact match after normalization
        if norm_spec in self.norm_to_spec:
            return True, self.norm_to_spec[norm_spec], []

        # If no exact match, get fuzzy matches
        matches = get_close_matches(norm_spec, self.norm_to_spec.keys(), n=3, cutoff=0.6)
        suggestions = [self.norm_to_spec[m] for m in matches]

        return False, norm_spec, suggestions

    def add_process(self, process: str, vendor_name: str = None) -> bool:
        """
        Add a new process to the reference.

        Args:
            process: The process name to add
            vendor_name: The name of the vendor to add the process to. If None, adds to all vendors.

        Returns:
            Whether the process was added successfully
        """
        # Normalize the process name
        norm_process = self.normalize(process)

        # Check if the process already exists
        if norm_process in self.norm_to_proc:
            return False

        # Add the process to the specified vendor or all vendors
        if vendor_name:
            for vendor in self.ref['vendors']:
                if vendor['name'] == vendor_name:
                    vendor['processes'].append({'name': process, 'specs': []})
                    break
        else:
            # If no vendor specified, add to the first vendor
            if self.ref['vendors']:
                self.ref['vendors'][0]['processes'].append({'name': process, 'specs': []})

        # Save the updated reference
        self._save_reference()

        # Rebuild the normalized maps
        self._build_normalized_maps()

        return True

    def add_spec(self, spec: str, process_name: str, vendor_name: str = None) -> bool:
        """
        Add a new spec to the reference.

        Args:
            spec: The spec name to add
            process_name: The name of the process to add the spec to
            vendor_name: The name of the vendor to add the spec to. If None, adds to all vendors with the process.

        Returns:
            Whether the spec was added successfully
        """
        # Normalize the spec name
        norm_spec = self.normalize(spec)

        # Check if the spec already exists
        if norm_spec in self.norm_to_spec:
            return False

        # Add the spec to the specified process in the specified vendor or all vendors
        added = False

        for vendor in self.ref['vendors']:
            if vendor_name and vendor['name'] != vendor_name:
                continue

            for process in vendor.get('processes', []):
                if self.normalize(process['name']) == self.normalize(process_name):
                    if process.get('specs') is None:
                        process['specs'] = []

                    process['specs'].append({'number': spec, 'familiar': True})
                    added = True

        if added:
            # Save the updated reference
            self._save_reference()

            # Rebuild the normalized maps
            self._build_normalized_maps()

        return added

    def _save_reference(self):
        """Save the reference data back to the YAML file."""
        with open(self.yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.ref, f, default_flow_style=False, sort_keys=False)

    def interactive_cli(self):
        """Run the interactive CLI."""
        console.print(Panel.fit(
            "[bold blue]Spec and Process Validator[/bold blue]\n\n"
            "This tool helps you validate and manage process and spec names against the reference data.",
            title="Welcome",
            border_style="green"
        ))

        while True:
            action = questionary.select(
                "What would you like to do?",
                choices=[
                    "Check a process or spec",
                    "Add a new process",
                    "Add a new spec",
                    "View all processes",
                    "View all specs",
                    "Exit"
                ]
            ).ask()

            if action == "Exit":
                console.print("[green]Goodbye![/green]")
                break

            elif action == "Check a process or spec":
                input_type = questionary.select(
                    "What would you like to check?",
                    choices=["Process", "Spec"]
                ).ask()

                user_input = questionary.text(
                    f"Enter the {input_type.lower()} to check:"
                ).ask()

                if input_type == "Process":
                    exists, normalized, suggestions = self.check_process(user_input)
                else:
                    exists, normalized, suggestions = self.check_spec(user_input)

                if exists:
                    console.print(Panel(f"✅ {input_type} '{user_input}' is valid.\nNormalized: '{normalized}'", 
                                 title=f"Valid {input_type}", border_style="green"))
                else:
                    console.print(Panel(f"❌ {input_type} '{user_input}' not found.\nNormalized: '{normalized}'", 
                                 title=f"Invalid {input_type}", border_style="red"))

                    if suggestions:
                        table = Table(title="Did you mean one of these?")
                        table.add_column("Suggestion")
                        for suggestion in suggestions:
                            table.add_row(suggestion)
                        console.print(table)
                    else:
                        console.print("[yellow]No similar items found.[/yellow]")

            elif action == "Add a new process":
                process_name = questionary.text(
                    "Enter the name of the process to add:"
                ).ask()

                # Ask if the process should be added to a specific vendor
                add_to_specific = questionary.confirm(
                    "Add to a specific vendor?",
                    default=False
                ).ask()

                vendor_name = None
                if add_to_specific:
                    # Get list of vendor names
                    vendor_names = [v['name'] for v in self.ref['vendors']]
                    vendor_name = questionary.select(
                        "Select the vendor:",
                        choices=vendor_names
                    ).ask()

                success = self.add_process(process_name, vendor_name)

                if success:
                    console.print(f"[green]✅ Process '{process_name}' added successfully.[/green]")
                else:
                    console.print(f"[red]❌ Process '{process_name}' already exists or could not be added.[/red]")

            elif action == "Add a new spec":
                spec_name = questionary.text(
                    "Enter the name of the spec to add:"
                ).ask()

                # Get list of process names
                process_names = list(self.processes)
                process_name = questionary.select(
                    "Select the process to add the spec to:",
                    choices=process_names
                ).ask()

                # Ask if the spec should be added to a specific vendor
                add_to_specific = questionary.confirm(
                    "Add to a specific vendor?",
                    default=False
                ).ask()

                vendor_name = None
                if add_to_specific:
                    # Get list of vendor names
                    vendor_names = [v['name'] for v in self.ref['vendors']]
                    vendor_name = questionary.select(
                        "Select the vendor:",
                        choices=vendor_names
                    ).ask()

                success = self.add_spec(spec_name, process_name, vendor_name)

                if success:
                    console.print(f"[green]✅ Spec '{spec_name}' added successfully to process '{process_name}'.[/green]")
                else:
                    console.print(f"[red]❌ Spec '{spec_name}' already exists or could not be added.[/red]")

            elif action == "View all processes":
                table = Table(title="All Processes")
                table.add_column("Process Name")

                for process in sorted(self.processes):
                    table.add_row(process)

                console.print(table)

            elif action == "View all specs":
                table = Table(title="All Specs")
                table.add_column("Spec Number")

                for spec in sorted(self.specs):
                    table.add_row(spec)

                console.print(table)


def main():
    """Command-line interface for the spec and process validator."""
    parser = argparse.ArgumentParser(description='Validate and normalize process and spec names.')

    # Add interactive mode flag
    parser.add_argument('--interactive', '-i', action='store_true', 
                        help='Run in interactive mode with a user-friendly interface')

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check a process or spec')
    check_parser.add_argument('--type', choices=['process', 'spec'], required=True,
                              help='Whether to check a process or spec')
    check_parser.add_argument('--value', required=True, help='The process or spec name to check')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new process or spec')
    add_parser.add_argument('--type', choices=['process', 'spec'], required=True,
                            help='Whether to add a process or spec')
    add_parser.add_argument('--value', required=True, help='The process or spec name to add')
    add_parser.add_argument('--process', help='The process to add the spec to (required for specs)')
    add_parser.add_argument('--vendor', help='The vendor to add the process or spec to')

    # Parse arguments
    args = parser.parse_args()

    # Initialize the validator
    validator = SpecProcessValidator()

    # Run in interactive mode if --interactive flag is set or no command is provided
    if args.interactive or not args.command:
        try:
            validator.interactive_cli()
        except Exception as e:
            # Check if it's a NoConsoleScreenBufferError
            if "NoConsoleScreenBufferError" in str(e):
                console.print("[red]Error: Cannot run interactive mode in this environment.[/red]")
                console.print("[yellow]This error typically occurs when running from an IDE or other non-console environment.[/yellow]")
                console.print("[yellow]Try running the script directly from a command prompt (cmd.exe) or PowerShell.[/yellow]")
                console.print("\n[green]Falling back to non-interactive mode. Use --help to see available commands.[/green]")
            else:
                # For other exceptions, just print the error
                console.print(f"[red]Error: {str(e)}[/red]")
            return

    # Non-interactive mode
    if args.command == 'check':
        if args.type == 'process':
            exists, normalized, suggestions = validator.check_process(args.value)
            if exists:
                console.print(f"[green]Process '{args.value}' is valid. Normalized: '{normalized}'[/green]")
            else:
                console.print(f"[red]Process '{args.value}' not found. Normalized: '{normalized}'[/red]")
                if suggestions:
                    console.print("[yellow]Did you mean one of these?[/yellow]")
                    for suggestion in suggestions:
                        console.print(f"  - {suggestion}")
                else:
                    console.print("[yellow]No similar processes found.[/yellow]")

        elif args.type == 'spec':
            exists, normalized, suggestions = validator.check_spec(args.value)
            if exists:
                console.print(f"[green]Spec '{args.value}' is valid. Normalized: '{normalized}'[/green]")
            else:
                console.print(f"[red]Spec '{args.value}' not found. Normalized: '{normalized}'[/red]")
                if suggestions:
                    console.print("[yellow]Did you mean one of these?[/yellow]")
                    for suggestion in suggestions:
                        console.print(f"  - {suggestion}")
                else:
                    console.print("[yellow]No similar specs found.[/yellow]")

    elif args.command == 'add':
        if args.type == 'process':
            success = validator.add_process(args.value, args.vendor)
            if success:
                console.print(f"[green]Process '{args.value}' added successfully.[/green]")
            else:
                console.print(f"[red]Process '{args.value}' already exists or could not be added.[/red]")

        elif args.type == 'spec':
            if not args.process:
                console.print("[red]Error: --process is required when adding a spec.[/red]")
                return

            success = validator.add_spec(args.value, args.process, args.vendor)
            if success:
                console.print(f"[green]Spec '{args.value}' added successfully to process '{args.process}'.[/green]")
            else:
                console.print(f"[red]Spec '{args.value}' already exists or could not be added.[/red]")


if __name__ == "__main__":
    main()
