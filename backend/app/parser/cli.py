import argparse
import sys
from app.core.database import SessionLocal, Base, engine
from app.parser.engine import parse_message
from app.parser.normalizer import normalize_sender
from app.parser.registry import get_registry
from app.parser.reparse import reparse_all

def run_tests():
    registry = get_registry()
    total_cases = 0
    passed_cases = 0
    failed_cases = 0

    print(f"\n================ Running Parser Corpus Test Suite ================")
    print(f"Loaded {len(registry.templates)} templates from YAML files.\n")

    for template_id, compiled in registry.templates.items():
        t_def = compiled.definition
        if not t_def.test_cases:
            continue

        print(f"Testing [{template_id}] ({t_def.issuer} {t_def.card_type}) - {len(t_def.test_cases)} cases:")
        for idx, tc in enumerate(t_def.test_cases, 1):
            total_cases += 1
            # Run parser against template test input
            # Use the first sender declared on the template as the sample sender
            sender = t_def.senders[0] if t_def.senders else "BANK"
            parsed = parse_message(sender=sender, body=tc.input)

            if not parsed:
                print(f"  ❌ Case {idx} FAILED: parse_message returned None")
                print(f"     Input: {tc.input}")
                failed_cases += 1
                continue

            failures = []
            exp = tc.expected
            if exp.amount_paise is not None and parsed.amount_paise != exp.amount_paise:
                failures.append(f"amount_paise expected {exp.amount_paise} got {parsed.amount_paise}")

            if exp.card_last4 is not None and parsed.card_last4 != exp.card_last4:
                failures.append(f"card_last4 expected '{exp.card_last4}' got '{parsed.card_last4}'")

            if exp.merchant is not None and parsed.merchant_clean != exp.merchant:
                failures.append(f"merchant expected '{exp.merchant}' got '{parsed.merchant_clean}'")

            if exp.transaction_type is not None and parsed.transaction_type != exp.transaction_type:
                failures.append(f"transaction_type expected '{exp.transaction_type}' got '{parsed.transaction_type}'")

            if exp.category_override is not None and parsed.category != exp.category_override:
                failures.append(f"category expected '{exp.category_override}' got '{parsed.category}'")

            if failures:
                print(f"  ❌ Case {idx} FAILED:")
                print(f"     Input: {tc.input}")
                for f in failures:
                    print(f"     - {f}")
                failed_cases += 1
            else:
                print(f"  ✅ Case {idx} PASSED")
                passed_cases += 1

    print("\n------------------------------------------------------------------")
    print(f"Total: {total_cases} | Passed: {passed_cases} | Failed: {failed_cases}")
    if failed_cases > 0:
        print("❌ Test suite FAILED")
        sys.exit(1)
    else:
        print("🎉 All corpus test cases PASSED!")
        sys.exit(0)

def sync_templates():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        registry = get_registry()
        count = registry.sync_to_db(db)
        print(f"Successfully synced {count} templates to SQLite database.")
    finally:
        db.close()

def run_reparse():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        stats = reparse_all(db)
        print(f"Reparse complete: {stats}")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Expense Tracker Parser CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("test", help="Run corpus test cases against all templates")
    subparsers.add_parser("sync", help="Sync YAML templates to SQLite database")
    subparsers.add_parser("reparse", help="Reparse all stored raw messages in database")

    args = parser.parse_args()
    if args.command == "test":
        run_tests()
    elif args.command == "sync":
        sync_templates()
    elif args.command == "reparse":
        run_reparse()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
