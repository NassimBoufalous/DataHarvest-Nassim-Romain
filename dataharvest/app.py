# dataharvest/app.py

import argparse
import json
import logging
import sys

from .config import Config
from .orchestrator import Orchestrator
from .store import Store

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("dataharvest")


def cmd_crawl(args):
    """Sous-commande `crawl` : lance Orchestrator.run() sur la config donnee."""
    try:
        config = Config(args.config)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"Config invalide : {e}")
        sys.exit(1)

    orch = Orchestrator(config)
    report = orch.run(dry_run=args.dry_run)

    if not args.dry_run:
        print(json.dumps(report, indent=2, ensure_ascii=False))


def cmd_export(args):
    """Sous-commande `export` : convertit un backend de stockage vers un autre."""
    src_path = getattr(args, "from")
    src_backend = _guess_backend(src_path)
    dst_backend = _guess_backend(args.to)

    store = Store(src_backend, src_path)
    n = store.export_to(dst_backend, args.to)
    log.info(f"{n} items exportes de {src_path} vers {args.to}")


def cmd_validate(args):
    """Sous-commande `validate` : charge une config et affiche un resume sans scraper."""
    try:
        config = Config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Config invalide : {e}")
        sys.exit(1)

    print(f"Config valide : {args.config}")
    print(f"  url        : {config.url}")
    print(f"  selectors  : {list(config.selectors.keys())}")
    print(f"  fetcher    : delay={config.fetcher.delay}s retries={config.fetcher.retries}")
    print(f"  store      : {config.store.backend} -> {config.store.path}")


def _guess_backend(path: str) -> str:
    if path.endswith(".csv"):
        return "csv"
    if path.endswith(".json"):
        return "json"
    if path.endswith((".db", ".sqlite", ".sqlite3")):
        return "sqlite"
    raise ValueError(f"Impossible de deviner le backend depuis le chemin : {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dataharvest")
    sub = parser.add_subparsers(dest="command", required=True)

    p_crawl = sub.add_parser("crawl", help="Lance le scraping complet selon une config")
    p_crawl.add_argument("--config", required=True, help="Chemin du fichier YAML/JSON")
    p_crawl.add_argument(
        "--dry-run", action="store_true",
        help="Fetche/parse uniquement la 1ere page, affiche les items sans stocker"
    )
    p_crawl.set_defaults(func=cmd_crawl)

    p_export = sub.add_parser("export", help="Exporte d'un backend vers un autre")
    p_export.add_argument("--from", dest="from", required=True, help="Fichier source")
    p_export.add_argument("--to", required=True, help="Fichier destination")
    p_export.set_defaults(func=cmd_export)

    p_validate = sub.add_parser("validate", help="Valide un fichier de config sans scraper")
    p_validate.add_argument("--config", required=True)
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()