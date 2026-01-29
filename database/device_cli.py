#!/usr/bin/env python3
"""
Command-line interface for device database management.

Provides commands for updating, validating, exporting, and managing device data.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from database.update_devices import (
    update_devices_from_json,
    export_devices_to_json
)
from database.validators import validate_devices_file, ValidationError
from database.connection import SessionLocal, check_connection
from database.models import Device


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_success(message: str):
    """Print success message."""
    print(f"✓ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"✗ {message}", file=sys.stderr)


def print_warning(message: str):
    """Print warning message."""
    print(f"⚠ {message}")


def print_stats(stats: dict):
    """Print update statistics."""
    print("\nUpdate Statistics:")
    print(f"  Inserted:  {stats['inserted']}")
    print(f"  Updated:   {stats['updated']}")
    print(f"  Skipped:   {stats['skipped']}")
    print(f"  Failed:    {stats['failed']}")
    print(f"  Total:     {stats['total_processed']}")
    
    if stats['errors']:
        print("\nErrors:")
        for error in stats['errors']:
            print(f"  - {error}")


def cmd_update(args):
    """Handle update command."""
    print_header("Device Database Update")
    
    # Check file exists
    json_file = Path(args.file)
    if not json_file.exists():
        print_error(f"File not found: {args.file}")
        return 1
    
    print(f"File: {args.file}")
    print(f"Mode: {'DRY RUN (no changes will be made)' if args.dry_run else 'LIVE UPDATE'}")
    
    # Check database connection
    print("\nChecking database connection...")
    conn_result = check_connection()
    if not conn_result["success"]:
        print_error(f"Database connection failed: {conn_result['error']}")
        return 1
    print_success("Database connection OK")
    
    # Perform update
    print("\nProcessing devices...")
    result = update_devices_from_json(args.file, dry_run=args.dry_run)
    
    # Print results
    print("\n" + "-" * 70)
    if result["success"]:
        print_success("Update completed successfully")
        print_stats(result["stats"])
        
        if args.dry_run:
            print("\n" + "=" * 70)
            print("  DRY RUN COMPLETE - No changes were made to the database")
            print("  Run without --dry-run to apply these changes")
            print("=" * 70)
    else:
        print_error(f"Update failed: {result.get('error', 'Unknown error')}")
        if "stats" in result:
            print_stats(result["stats"])
        return 1
    
    return 0


def cmd_validate(args):
    """Handle validate command."""
    print_header("JSON Validation")
    
    # Check file exists
    json_file = Path(args.file)
    if not json_file.exists():
        print_error(f"File not found: {args.file}")
        return 1
    
    print(f"File: {args.file}\n")
    
    # Validate
    try:
        result = validate_devices_file(args.file)
        print_success("Validation passed")
        print(f"\nDevices found: {result['data']['device_count']}")
        
        if result['data'].get('version'):
            print(f"Version: {result['data']['version']}")
        if result['data'].get('updated_at'):
            print(f"Updated at: {result['data']['updated_at']}")
        
        return 0
    
    except ValidationError as e:
        print_error("Validation failed")
        print(f"\n{str(e)}")
        return 1


def cmd_export(args):
    """Handle export command."""
    print_header("Export Devices to JSON")
    
    output_file = Path(args.output)
    
    # Check if output file exists
    if output_file.exists() and not args.force:
        print_error(f"File already exists: {args.output}")
        print("Use --force to overwrite")
        return 1
    
    print(f"Output: {args.output}\n")
    
    # Check database connection
    print("Checking database connection...")
    conn_result = check_connection()
    if not conn_result["success"]:
        print_error(f"Database connection failed: {conn_result['error']}")
        return 1
    print_success("Database connection OK")
    
    # Export
    print("\nExporting devices...")
    result = export_devices_to_json(args.output)
    
    if result["success"]:
        print_success(f"Exported {result['device_count']} devices to {args.output}")
        return 0
    else:
        print_error(f"Export failed: {result.get('error', 'Unknown error')}")
        return 1


def cmd_stats(args):
    """Handle stats command."""
    print_header("Device Database Statistics")
    
    # Check database connection
    print("Checking database connection...")
    conn_result = check_connection()
    if not conn_result["success"]:
        print_error(f"Database connection failed: {conn_result['error']}")
        return 1
    print_success("Database connection OK\n")
    
    # Get statistics
    db = SessionLocal()
    try:
        total_devices = db.query(Device).count()
        
        # Count by vendor
        from sqlalchemy import func
        vendor_counts = db.query(
            Device.vendor,
            func.count(Device.id).label('count')
        ).group_by(Device.vendor).order_by(func.count(Device.id).desc()).all()
        
        # Count by device type
        type_counts = db.query(
            Device.device_type,
            func.count(Device.id).label('count')
        ).group_by(Device.device_type).order_by(func.count(Device.id).desc()).all()
        
        print(f"Total Devices: {total_devices}\n")
        
        if vendor_counts:
            print("Devices by Vendor:")
            for vendor, count in vendor_counts:
                print(f"  {vendor:20s} {count:4d}")
        
        if type_counts:
            print("\nDevices by Type:")
            for device_type, count in type_counts:
                print(f"  {device_type:20s} {count:4d}")
        
        db.close()
        return 0
    
    except Exception as e:
        print_error(f"Failed to get statistics: {str(e)}")
        db.close()
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Device database management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate JSON file
  python device_cli.py validate devices.json
  
  # Preview changes (dry run)
  python device_cli.py update devices.json --dry-run
  
  # Apply updates to database
  python device_cli.py update devices.json
  
  # Export current devices
  python device_cli.py export backup.json
  
  # Show database statistics
  python device_cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True
    
    # Update command
    update_parser = subparsers.add_parser(
        'update',
        help='Update devices from JSON file'
    )
    update_parser.add_argument(
        'file',
        help='Path to JSON file containing device data'
    )
    update_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying database'
    )
    update_parser.set_defaults(func=cmd_update)
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate JSON file without updating database'
    )
    validate_parser.add_argument(
        'file',
        help='Path to JSON file to validate'
    )
    validate_parser.set_defaults(func=cmd_validate)
    
    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export current devices to JSON file'
    )
    export_parser.add_argument(
        'output',
        help='Output JSON file path'
    )
    export_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite output file if it exists'
    )
    export_parser.set_defaults(func=cmd_export)
    
    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Show database statistics'
    )
    stats_parser.set_defaults(func=cmd_stats)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    try:
        exit_code = args.func(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
