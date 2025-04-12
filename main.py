#!/usr/bin/env python3
"""
Entry point for the Router Network Interface Monitor.
Handles argument parsing and orchestrates the monitoring process.
"""

import os
import sys
import asyncio
import argparse
import time
import ipaddress
from typing import List, Tuple
import logging

from .config import load_config, Config
from .db.schema import create_database_tables
from .db.router_dao import save_failed_routers
from snmp.client import check_snmp_tools_installed
from .models.router import process_router
from .util.logging import setup_logging

logger = logging.getLogger(__name__)

def read_router_ips(filename: str) -> List[str]:
    """Read router IP addresses from a file."""
    router_ips = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                # Remove comments and strip whitespace
                line = line.split('#')[0].strip()
                if not line:
                    continue
                
                try:
                    # Validate IP address
                    ip = ipaddress.ip_address(line)
                    router_ips.append(str(ip))
                except ValueError:
                    logger.warning(f"Invalid IP address in {filename}: {line}")
    except FileNotFoundError:
        logger.error(f"Router file not found: {filename}")
    
    return router_ips

async def process_routers(router_ips: List[str], config: Config) -> Tuple[int, int]:
    """Process all routers with concurrency control."""
    logger.info(f"Processing {len(router_ips)} routers with max concurrency {config.max_concurrent_routers}")
    
    # Use semaphore to limit concurrency
    semaphore = asyncio.Semaphore(config.max_concurrent_routers)
    failed_routers = []
    successful_count = 0
    
    async def process_router_with_semaphore(router_ip):
        nonlocal successful_count
        async with semaphore:
            success = await process_router(router_ip, config)
            if success:
                successful_count += 1
            else:
                failed_routers.append(router_ip)
    
    # Create tasks for all routers
    tasks = [process_router_with_semaphore(ip) for ip in router_ips]
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    
    # Save failed routers to file
    if failed_routers:
        save_failed_routers(failed_routers, config.failed_routers_file)
    
    return successful_count, len(failed_routers)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Router Network Interface Monitor')
    parser.add_argument('-r', '--routers', default='routers.txt', 
                        help='File containing router IP addresses (default: routers.txt)')
    parser.add_argument('-c', '--community', help='SNMP community string (overrides config file)')
    parser.add_argument('-p', '--port', type=int, help='SNMP port (overrides config file)')
    parser.add_argument('-t', '--timeout', type=int, help='SNMP timeout in seconds (overrides config file)')
    parser.add_argument('--retries', type=int, help='SNMP retries (overrides config file)')
    parser.add_argument('--max-concurrent', type=int, 
                        help='Maximum number of concurrent router operations (overrides config file)')
    parser.add_argument('--db-setup', action='store_true', 
                        help='Set up database tables only (does not process routers)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    return parser.parse_args()

async def main():
    """Main function."""
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.verbose)
    logger.debug("Verbose logging enabled" if args.verbose else "Standard logging enabled")
    
    # Load configuration
    config = load_config()
    
    # Override config with command line arguments if provided
    if args.community:
        config.community = args.community
    if args.port:
        config.port = args.port
    if args.timeout:
        config.timeout = args.timeout
    if args.retries:
        config.retries = args.retries
    if args.max_concurrent:
        config.max_concurrent_routers = args.max_concurrent
    
    # Check for SNMP tools
    if not await check_snmp_tools_installed():
        logger.error("SNMP tools (net-snmp) not installed. Please install them and try again.")
        sys.exit(1)
    
    # Set up database
    if not await create_database_tables(config):
        logger.error("Failed to set up database tables")
        sys.exit(1)
    
    # If only setting up database, exit
    if args.db_setup:
        logger.info("Database setup complete")
        return
    
    # Read router IPs
    router_ips = read_router_ips(args.routers)
    if not router_ips:
        logger.error(f"No valid router IP addresses found in {args.routers}")
        sys.exit(1)
    
    logger.info(f"Found {len(router_ips)} router IP addresses to process")
    
    # Process routers
    start_time = time.time()
    successful, failed = await process_routers(router_ips, config)
    end_time = time.time()
    
    logger.info(f"Processed {len(router_ips)} routers in {end_time - start_time:.2f} seconds")
    logger.info(f"Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(main())