#!/usr/bin/env python3
"""
immich_replay.py

Extracts EXIF transaction data from immich_extract log files and outputs a CSV suitable for replaying EXIF operations.

Usage:
    python immich_replay.py --input <immich_extract.log> [--output <output.csv>] [--last] [--failed]

Arguments:
    --input   Input log file from immich_extract.py (default: latest in .log if --last)
    --output  Output CSV file (default: .log/immich_replay_{original timestamp}_{current timestamp}.csv)
    --last    Use latest immich_extract log in .log directory
    --failed  Include only failed transactions (status=error)

"""
import sys
import os
import re
import csv
import glob
from pathlib import Path
from datetime import datetime

# Import ScriptArgumentParser from COMMON
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))
from common.argument_parser import ScriptArgumentParser
from common.logging import ScriptLogging

SCRIPT_INFO = {
    'name': 'immich_replay',
    'description': 'Extract EXIF transaction data from immich_extract log files and output a CSV for replay.',
    'examples': [
        '--input .log/immich_extract_20251024_232451.log',
        '--last --failed',
        '--input mylog.log --output replay.csv'
    ]
}

SCRIPT_ARGUMENTS = {
    'input': {
        'flag': '--input',
        'help': 'Input log file from immich_extract.py',
        'required': False
    },
    'output': {
        'flag': '--output',
        'help': 'Output CSV file for replay data',
        'required': False
    },
    'last': {
        'flag': '--last',
        'action': 'store_true',
        'help': 'Use latest immich_extract log in .log directory'
    },
    'failed': {
        'flag': '--failed',
        'action': 'store_true',
        'help': 'Include only failed transactions (status=error)'
    }
}

def find_latest_log():
    log_dir = Path(__file__).resolve().parent.parent / '.log'
    logs = sorted(glob.glob(str(log_dir / 'immich_extract_*.log')))
    if logs:
        return logs[-1]
    return None

def parse_exif_log_line(line):
    # Accept lines where the EXIF audit payload is embedded in a longer log line.
    # Expected payload format (CSV-like): [EXIF],{path},{status},{current desc},{target desc},{current tags},{target tags},{current date},{target date},{error}
    # The file log lines usually look like: "2025-10-25 18:02:09 - AUDIT - [EXIF],/path,..."
    idx = line.find('[EXIF],')
    if idx == -1:
        return None
    payload = line[idx:]
    parts = payload.strip().split(',', 9)
    if len(parts) < 10:
        return None
    return {
        'file_path': parts[1],
        'status': parts[2],
        'current_desc': parts[3],
        'target_desc': parts[4],
        'current_tags': parts[5],
        'target_tags': parts[6],
        'current_date': parts[7],
        'target_date': parts[8],
        'error': parts[9],
    }

def main():
    parser = ScriptArgumentParser(SCRIPT_INFO, SCRIPT_ARGUMENTS)
    args = parser.parse_args()
    # Custom argument resolution: --input and --output are optional if --last is given
    logger = parser.setup_logging(vars(args), 'immich_replay')

    # Determine input log file
    if getattr(args, 'last', False) or not getattr(args, 'input', None):
        latest = find_latest_log()
        if not latest:
            logger.error('No immich_extract_*.log files found in .log directory.')
            sys.exit(1)
        input_log = latest
    else:
        input_log = args.input
    if not input_log or not os.path.exists(input_log):
        logger.error(f'Input log file not found: {input_log}')
        sys.exit(1)

    # Determine output CSV file
    if getattr(args, 'output', None):
        output_csv = args.output
    else:
        m = re.search(r'immich_extract_(\d{8}_\d{6})', os.path.basename(input_log))
        orig_ts = m.group(1) if m else 'unknown'
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_csv = f'.log/immich_replay_{orig_ts}_{now_ts}.csv'

    # Parse log and extract EXIF lines
    exif_rows = []
    with open(input_log, 'r') as f:
        for line in f:
            row = parse_exif_log_line(line)
            if row:
                if args.failed and row['status'] != 'error':
                    continue
                exif_rows.append(row)

    if not exif_rows:
        logger.warning('No [EXIF] log lines found in input log.')
    else:
        with open(output_csv, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'file_path', 'status', 'current_desc', 'target_desc', 'current_tags', 'target_tags', 'current_date', 'target_date', 'error'
            ])
            writer.writeheader()
            for row in exif_rows:
                writer.writerow(row)
        logger.info(f'Extracted {len(exif_rows)} EXIF transactions to {output_csv}')

    # Print replay command for user
    cmd = f'python immich_replay.py --input "{input_log}" --output "{output_csv}"'
    if args.failed:
        cmd += ' --failed'
    logger.info(f'To replay: {cmd}')

if __name__ == '__main__':
    main()
