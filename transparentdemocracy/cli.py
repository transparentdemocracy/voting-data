from argparse import ArgumentParser

from transparentdemocracy.politicians.serialization import create_json, print_politicians_by_party


def main():
    parser = ArgumentParser("td", "td <subcommand> [options]", "CLI tool to process voting data")
    subparsers = parser.add_subparsers(title="td")

    add_politicians_subcommand(subparsers)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


def add_politicians_subcommand(subs):
    parser = subs.add_parser('politicians', help="Commands to process politicians json files")
    sub_parsers = parser.add_subparsers(title="operations", description="valid operations", help="Plenaries subcommands")

    json = sub_parsers.add_parser('json', help="Write politicians json")
    json.set_defaults(func=lambda args: create_json())

    print_by_party = sub_parsers.add_parser('print-by-party', help="Print politicians by party")
    print_by_party.set_defaults(func=lambda args: print_politicians_by_party())


if __name__ == "__main__":
    main()
