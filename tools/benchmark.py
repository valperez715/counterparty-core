#!/usr/bin/python3


import os
import time
import difflib

import apsw


MAX_INT = 2**63 - 1

def remove_from_balanc_old(db, address, asset, quantity):
    balance_cursor = db.cursor()

    balance_cursor.execute('''SELECT quantity FROM old_balances
                           WHERE (address = ? AND asset = ?)''', (address, asset))
    balances = balance_cursor.fetchall()
    if not len(balances) == 1:
        old_balance = 0
    else:
        old_balance = balances[0][0]

    if old_balance < quantity:
        raise Exception('Insufficient funds.')

    balance = round(old_balance - quantity)
    balance = min(balance, MAX_INT)
    assert balance >= 0

    bindings = {
        'quantity': balance,
        'address': address,
        'asset': asset
    }
    sql='update old_balances set quantity = :quantity where (address = :address and asset = :asset)'
    balance_cursor.execute(sql, bindings)


def add_to_balance_old(db, address, asset, quantity):
    balance_cursor = db.cursor()

    balance_cursor.execute('''SELECT quantity FROM old_balances \
                             WHERE (address = ? AND asset = ?)''', (address, asset))
    balances = balance_cursor.fetchall()
    if len(balances) == 0:
        assert balances == []

        #update balances table with new balance
        bindings = {
            'address': address,
            'asset': asset,
            'quantity': quantity,
        }
        sql='insert into old_balances values(:address, :asset, :quantity)'
        balance_cursor.execute(sql, bindings)
    elif len(balances) > 1:
        assert False
    else:
        old_balance = balances[0][0]
        assert type(old_balance) == int
        balance = round(old_balance + quantity)
        balance = min(balance, MAX_INT)

        bindings = {
            'quantity': balance,
            'address': address,
            'asset': asset
        }
        sql='update old_balances set quantity = :quantity where (address = :address and asset = :asset)'
        balance_cursor.execute(sql, bindings)


def get_balance_new(db, address, asset):
    """Get balance of contract or address."""
    cursor = db.cursor()
    # rowid is enough but let's be verbose
    balances = list(cursor.execute('''SELECT quantity FROM new_balances
                                   WHERE (address = ? AND asset = ?)
                                   ORDER BY block_index DESC, tx_index DESC, rowid DESC LIMIT 1''', (address, asset)))
    cursor.close()
    if not balances:
        return 0
    return balances[0][0]


def remove_from_balance_new(db, address, asset, quantity, block_index, tx_index):
    balance_cursor = db.cursor()

    old_balance = get_balance_new(db, address, asset)

    if old_balance < quantity:
        raise Exception('Insufficient funds.')

    balance = round(old_balance - quantity)
    balance = min(balance, MAX_INT)
    assert balance >= 0

    bindings = {
        'quantity': balance,
        'address': address,
        'asset': asset,
        'block_index': block_index,
        'tx_index': tx_index,
    }
    sql='INSERT INTO new_balances VALUES (:address, :asset, :quantity, :block_index, :tx_index)'
    balance_cursor.execute(sql, bindings)


def add_to_balance_new(db, address, asset, quantity, block_index, tx_index):
    balance_cursor = db.cursor()

    old_balance = get_balance_new(db, address, asset)
    balance = round(old_balance + quantity)
    balance = min(balance, MAX_INT)

    bindings = {
        'quantity': balance,
        'address': address,
        'asset': asset,
        'block_index': block_index,
        'tx_index': tx_index,
    }
    sql='INSERT INTO new_balances VALUES (:address, :asset, :quantity, :block_index, :tx_index)'
    balance_cursor.execute(sql, bindings)


def copy_memory_db_to_disk(local_base, memory_db):
    print("Copying in memory database to disk...")
    start_time_copy_db = time.time()
    # backup old database
    if os.path.exists(local_base):
        os.remove(local_base)
    # initialize new database
    db = apsw.Connection(local_base)
    # copy memory database to new database
    with db.backup("main", memory_db, "main") as backup:
        while not backup.done:
            backup.step(100)
    print('Database copy duration: {:.3f}s'.format(time.time() - start_time_copy_db))


def prepare_benchmark_db(database_file):
    print(f"Opening {database_file} database...")
    db = apsw.Connection(database_file, flags=apsw.SQLITE_OPEN_READONLY)
    cursor = db.cursor()

    credits_count = cursor.execute("SELECT count(*) as cnt FROM credits").fetchone()[0]
    debits_count = cursor.execute("SELECT count(*) as cnt FROM debits").fetchone()[0]
    movements_count = credits_count + debits_count

    print("Credits count:", credits_count)
    print("Debits count:", debits_count)
    print("Total:", movements_count)

    print()

    print("Creating in memory database...")

    bench_db = apsw.Connection(":memory:")
    bench_cursor = bench_db.cursor()

    bench_cursor.execute('''CREATE TABLE IF NOT EXISTS new_balances(
                      address TEXT,
                      asset TEXT,
                      quantity INTEGER,
                      block_index INTEGER,
                      tx_index INTEGER)
                   ''')
    bench_cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_asset_idx ON new_balances (address, asset)
                   ''')
    bench_cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_idx ON new_balances (address)
                   ''')
    bench_cursor.execute('''CREATE INDEX IF NOT EXISTS
                      asset_idx ON new_balances (asset)
                   ''')
    
    bench_cursor.execute('''CREATE TABLE IF NOT EXISTS old_balances(
                      address TEXT,
                      asset TEXT,
                      quantity INTEGER)
                   ''')
    bench_cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_asset_idx ON old_balances (address, asset)
                   ''')
    bench_cursor.execute('''CREATE INDEX IF NOT EXISTS
                      address_idx ON old_balances (address)
                   ''')
    bench_cursor.execute('''CREATE INDEX IF NOT EXISTS
                      asset_idx ON old_balances (asset)
                   ''')

    query = """
            SELECT * FROM
                (SELECT 'credit' as table_name, address, asset, quantity, block_index FROM credits
                    UNION ALL
                SELECT 'debits' as table_name, address, asset, quantity, block_index FROM debits)
            ORDER BY block_index
            """
    
    """ cursor.execute(query)
    count = 1
    populate_start_time = time.time()
    print("Populating `old_balances`...")
    for movement in cursor:
        if movement[0] == 'credit':
            add_to_balance_old(bench_db, *movement[1:4])
        else:
            remove_from_balanc_old(bench_db, *movement[1:4])
        print(f"{count}/{movements_count}", end="\r")
        count += 1
    print('`old_balances` populated in: {:.3f}s'.format(time.time() - populate_start_time)) """
    
    cursor.execute(query)
    count = 1
    populate_start_time = time.time()
    print("Populating `new_balances`...")
    for movement in cursor:
        if movement[0] == 'credit':
            add_to_balance_new(bench_db, *movement[1:], 0)
        else:
            remove_from_balance_new(bench_db, *movement[1:], 0)
        print(f"{count}/{movements_count}", end="\r")
        count += 1
    print('`new_balances` populated in: {:.3f}s'.format(time.time() - populate_start_time))
    
    copy_memory_db_to_disk(BENCHMARK_DB, bench_db)
    print()


def compare_strings(string1, string2):
    """Compare strings diff-style."""
    diff = list(difflib.unified_diff(string1.splitlines(1), string2.splitlines(1), n=0))
    if len(diff):
        print(f"\n{len(diff)} Differences:")
        print("\n".join(diff))
        print(f"\n{len(diff)} differences")
    return len(diff)


BALANCES_VIEW_QUERY = """
    SELECT address, asset, quantity, (address || asset) AS aa, MAX(rowid)
    FROM new_balances
    GROUP BY aa
"""

def benchmark_new_balances():
    
    db = apsw.Connection(BENCHMARK_DB, flags=apsw.SQLITE_OPEN_READONLY)
    cursor = db.cursor()

    rows_in_old_balances = cursor.execute("SELECT count(*) as cnt FROM old_balances").fetchone()[0]
    print("Rows in `old_balances`:", rows_in_old_balances)
    rows_in_new_balances = cursor.execute("SELECT count(*) as cnt FROM new_balances").fetchone()[0]
    print("Rows in `new_balances`:", rows_in_new_balances)
    print()

    print("Getting 1000 addresses with most assets from `old_balances`...")
    start_time = time.time()
    balances = cursor.execute("""
                              SELECT address, count(asset) as cnt
                              FROM old_balances
                              GROUP BY address
                              ORDER BY cnt DESC
                              LIMIT 1000
                              """).fetchall()

    print('Duration: {:.3f}s'.format(time.time() - start_time))
    print()

    print("Get balances for 1000 addresses with most assets from `old_balances`...")
    start_time = time.time()
    old_balances = []
    count_old = 0
    for balance in balances:
        address_balances = cursor.execute("""
                        SELECT asset, quantity FROM old_balances
                        WHERE address = ?
                        ORDER BY asset
                        """, (balance[0],)).fetchall()
        count_old += len(address_balances)
        old_balances.append("\n".join([", ".join([str(x) for x in address_balance]) for address_balance in address_balances]))
    print('Duration: {:.3f}s'.format(time.time() - start_time))
    print()

    print("Getting 1000 addresses with most assets from `new_balances`...")
    start_time = time.time()
    balances = cursor.execute(f"""
                                  SELECT address, count(asset) as cnt
                                  FROM ({BALANCES_VIEW_QUERY})
                                  GROUP BY address
                                  ORDER BY cnt DESC
                                  LIMIT 1000
                                  """).fetchall()
    #with open("new_balances_addresses.txt", "w") as f:
    #    f.write("\n".join([balance[0] for balance in balances]))

    print('Duration: {:.3f}s'.format(time.time() - start_time))
    print()

    print("Get balances for 1000 addresses with most assets from `new_balances`...")
    start_time = time.time()
    new_balances = []
    count_new = 0
    for balance in balances:
        address_balances = cursor.execute(f"""
                        SELECT asset, quantity, (address || asset) AS aa, MAX(rowid)
                        FROM new_balances
                        WHERE address = ?
                        GROUP BY aa
                        ORDER BY asset
                        """, (balance[0],)).fetchall()
        count_new += len(address_balances)
        new_balances.append("\n".join([", ".join([str(x) for x in address_balance]) for address_balance in address_balances]))
    print('Duration: {:.3f}s'.format(time.time() - start_time))
    print()

BENCHMARK_DB="/home/tower/benchmark.db"

#prepare_benchmark_db("/home/tower/counterparty.testnet.bootstrap.db")
prepare_benchmark_db("/home/tower/counterparty.db")
#benchmark_new_balances()

