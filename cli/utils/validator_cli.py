import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.validation.validator import SpecValidator

console = Console()


class CLISpecValidator(SpecValidator):
    """
    CLI extension of the SpecValidator that adds interactive functionality.

    This class extends the core validator with methods for interactive CLI usage,
    including rich text formatting and questionary prompts.
    """

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
                    console.print(
                        f"[green]✅ Spec '{spec_name}' added successfully to process '{process_name}'.[/green]")
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
    import argparse

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
    validator = CLISpecValidator()

    # Run in interactive mode if --interactive flag is set or no command is provided
    if args.interactive or not args.command:
        try:
            validator.interactive_cli()
        except Exception as e:
            # Check if it's a NoConsoleScreenBufferError
            if "NoConsoleScreenBufferError" in str(e):
                console.print("[red]Error: Cannot run interactive mode in this environment.[/red]")
                console.print(
                    "[yellow]This error typically occurs when running from an IDE or other non-console environment.[/yellow]")
                console.print(
                    "[yellow]Try running the script directly from a command prompt (cmd.exe) or PowerShell.[/yellow]")
                console.print(
                    "\n[green]Falling back to non-interactive mode. Use --help to see available commands.[/green]")
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