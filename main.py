import argparse
import os
import sys

from torrentfile.torrentfile import parse_torrent  # Torrent metadata parser

def main():
    """Command-line interface for BitTorrent client."""
    # Configure argument parser
    p = argparse.ArgumentParser(
        description="Download a .torrent via plain-Python BitTorrent"
    )
    p.add_argument(
        "-t", "--torrent",
        help="Path to .torrent file (default: %(default)s)"
    )
    p.add_argument(
        "-o", "--output",
        help="Output path (file or directory)",
    )
    p.add_argument(
        "-p", "--port",
        type=int,
        help="Tracker announcement port (default: %(default)s)"
    )
    args = p.parse_args()

    # Parse torrent metadata
    try:
        with open(args.torrent, "rb") as f:
            tf = parse_torrent(f)
    except Exception as e:
        print(f"Error reading torrent file: {e}", file=sys.stderr)
        sys.exit(1)  # Standard error exit code

    # Determine output path strategy:
    # - Use explicit filename if provided
    # - Use torrent name in directory if path is folder
    # - Fallback to torrent name in CWD
    out_path = args.output or tf.name
    if os.path.isdir(out_path):
        out_path = os.path.join(out_path, tf.name)

    # Execute download workflow
    try:
        tf.download_to_file(out_path, port=args.port)
        print(f"Successfully saved to {out_path}")
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)  # Maintain error consistency

if __name__ == "__main__":
    main()  # Launch CLI interface