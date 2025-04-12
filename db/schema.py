"""
Database schema creation and maintenance for the Router Network Interface Monitor.
"""

import logging
from datetime import datetime, timedelta

from mysql.connector import Error

from ..config import Config
from .connection import db_connection, execute_with_retry, initialize_connection_pool

logger = logging.getLogger(__name__)

async def create_database_tables(config: Config) -> bool:
    """Create the normalized database tables with time-based partitioning if configured."""
    try:
        # Initialize connection pool first
        initialize_connection_pool(config)
        
        with db_connection(config) as connection:
            cursor = connection.cursor()
            execute_with_retry(cursor, f"CREATE DATABASE IF NOT EXISTS {config.db_name}")
            connection.commit()
            
            execute_with_retry(cursor, f"USE {config.db_name}")
            
            # Create routers table
            execute_with_retry(cursor, """
            CREATE TABLE IF NOT EXISTS routers (
                router_id INT AUTO_INCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                sysName VARCHAR(255),
                sysDescr TEXT,
                sysUpTime BIGINT,
                sysLocation VARCHAR(255),
                sysContact VARCHAR(255),
                sysObjectID VARCHAR(255),
                PRIMARY KEY (router_id),
                UNIQUE INDEX (ip_address),
                INDEX (last_update)
            ) ENGINE=InnoDB
            """)
            
            # Create interfaces table
            execute_with_retry(cursor, """
            CREATE TABLE IF NOT EXISTS interfaces (
                interface_id INT AUTO_INCREMENT,
                router_id INT NOT NULL,
                ifIndex BIGINT NOT NULL,
                ifName VARCHAR(255),
                ifDescr VARCHAR(255),
                ifType VARCHAR(50),
                ifMTU INT,
                ifSpeed BIGINT,
                ifPhysAddress VARCHAR(255),
                ifHighSpeed BIGINT,
                ifAlias VARCHAR(255),
                ipAddresses TEXT,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (interface_id),
                UNIQUE INDEX (router_id, ifIndex),
                FOREIGN KEY (router_id) REFERENCES routers(router_id) ON DELETE CASCADE,
                INDEX (last_update)
            ) ENGINE=InnoDB
            """)
            
            # Check if interface_stats table exists
            execute_with_retry(cursor, "SHOW TABLES LIKE 'interface_stats'")
            table_exists = cursor.fetchone() is not None
            
            # Create interface_stats table with partitioning if needed
            if not table_exists:
                create_stats_table_query = """
                CREATE TABLE interface_stats (
                    stat_id INT AUTO_INCREMENT,
                    interface_id INT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ifAdminStatus INT,
                    ifOperStatus INT,
                    ifInOctets BIGINT,
                    ifOutOctets BIGINT,
                    ifHCInOctets BIGINT,
                    ifHCOutOctets BIGINT,
                    PRIMARY KEY (stat_id),
                    FOREIGN KEY (interface_id) REFERENCES interfaces(interface_id) ON DELETE CASCADE,
                    INDEX (interface_id, timestamp),
                    INDEX (timestamp)
                ) ENGINE=InnoDB
                """
                
                # Add partitioning if configured
                if config.partition_interval_days > 0:
                    create_stats_table_query += """
                    PARTITION BY RANGE (TO_DAYS(timestamp)) (
                        PARTITION p_default VALUES LESS THAN (TO_DAYS('2020-01-01'))
                    )
                    """
                    
                execute_with_retry(cursor, create_stats_table_query)
                
                # Create partitions for current and future periods if partitioning is enabled
                if config.partition_interval_days > 0:
                    create_time_partitions(cursor, config.partition_interval_days)
                    
                logger.info("Created interface_stats table" + 
                           (" with time-based partitioning" if config.partition_interval_days > 0 else ""))
            
            # Add a maintenance function to add new partitions as time progresses
            if config.partition_interval_days > 0:
                maintain_partitions(cursor, config.partition_interval_days)
            
            connection.commit()
            logger.info("Database tables created or verified successfully.")
            return True
    except Error as e:
        logger.error(f"Error creating database tables: {e}")
        return False

def create_time_partitions(cursor, interval_days: int, num_partitions: int = 6):
    """Create time-based partitions for the interface_stats table."""
    logger.info(f"Creating time-based partitions with {interval_days} day interval")
    
    # Add partitions for current period and next few periods
    current_date = datetime.now().date()
    for i in range(num_partitions):
        partition_start = current_date + timedelta(days=i * interval_days)
        partition_end = current_date + timedelta(days=(i + 1) * interval_days)
        partition_name = f"p_{partition_start.strftime('%Y%m%d')}"
        
        # Check if partition already exists before trying to create it
        cursor.execute(
            "SELECT PARTITION_NAME FROM information_schema.partitions "
            "WHERE TABLE_NAME='interface_stats' AND PARTITION_NAME=%s",
            (partition_name,)
        )
        if cursor.fetchone() is None:
            add_partition_query = f"""
            ALTER TABLE interface_stats ADD PARTITION (
                PARTITION {partition_name} VALUES LESS THAN (TO_DAYS('{partition_end.strftime('%Y-%m-%d')}'))
            )
            """
            execute_with_retry(cursor, add_partition_query)
            logger.info(f"Added partition {partition_name} for date range {partition_start} to {partition_end}")
        else:
            logger.debug(f"Partition {partition_name} already exists")

def maintain_partitions(cursor, interval_days: int):
    """Check and add new partitions if needed."""
    try:
        # Get current partition information
        cursor.execute(
            "SELECT PARTITION_NAME, PARTITION_DESCRIPTION FROM information_schema.partitions "
            "WHERE TABLE_NAME='interface_stats' AND PARTITION_NAME != 'p_default' "
            "ORDER BY PARTITION_DESCRIPTION DESC LIMIT 1"
        )
        result = cursor.fetchone()
        
        if result and result[1]:
            partition_name, partition_desc = result
            
            # Convert PARTITION_DESCRIPTION (which contains TO_DAYS value) back to date
            cursor.execute(f"SELECT FROM_DAYS({partition_desc})")
            last_partition_date_str = cursor.fetchone()[0]
            last_partition_date = datetime.strptime(last_partition_date_str, '%Y-%m-%d').date()
            
            # Get the current date and calculate how many days ahead we have partitions for
            current_date = datetime.now().date()
            days_ahead = (last_partition_date - current_date).days
            
            # If we have less than 3 intervals of partitions ahead, add a new one
            if days_ahead < interval_days * 3:
                # Add one more partition
                new_partition_start = last_partition_date
                new_partition_end = new_partition_start + timedelta(days=interval_days)
                new_partition_name = f"p_{new_partition_start.strftime('%Y%m%d')}"
                
                # Make sure the partition doesn't already exist to avoid errors
                cursor.execute(
                    "SELECT PARTITION_NAME FROM information_schema.partitions "
                    "WHERE TABLE_NAME='interface_stats' AND PARTITION_NAME=%s",
                    (new_partition_name,)
                )
                if cursor.fetchone() is None:
                    add_partition_query = f"""
                    ALTER TABLE interface_stats ADD PARTITION (
                        PARTITION {new_partition_name} VALUES LESS THAN (TO_DAYS('{new_partition_end.strftime('%Y-%m-%d')}'))
                    )
                    """
                    execute_with_retry(cursor, add_partition_query)
                    logger.info(f"Added new partition {new_partition_name} for date range {new_partition_start} to {new_partition_end}")
        else:
            logger.warning("No existing partitions found. Creating initial partitions.")
            create_time_partitions(cursor, interval_days)
    except Error as e:
        logger.error(f"Error maintaining partitions: {e}")