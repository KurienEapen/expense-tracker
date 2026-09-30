import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern
import yaml
from sqlalchemy.orm import Session

from app.models.template import ParserTemplateModel
from app.parser.models import TemplateDefinition
from app.parser.normalizer import normalize_sender

logger = logging.getLogger(__name__)

# Default templates directory path (relative to repo root or backend root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

class CompiledTemplate:
    def __init__(self, definition: TemplateDefinition):
        self.definition = definition
        # Compile regex with ignore case and dotall/multiline
        self.compiled_regex: Pattern = re.compile(definition.regex, re.IGNORECASE)

class TemplateRegistry:
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.templates: Dict[str, CompiledTemplate] = {}
        self.sender_index: Dict[str, List[CompiledTemplate]] = {}
        self.load_from_yaml()

    def load_from_yaml(self) -> int:
        """
        Loads and compiles all YAML template definitions from the templates directory.
        """
        self.templates.clear()
        self.sender_index.clear()

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory {self.templates_dir} does not exist.")
            return 0

        count = 0
        for yaml_file in sorted(self.templates_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                if not data or not isinstance(data, list):
                    continue

                for item in data:
                    template_def = TemplateDefinition(**item)
                    compiled = CompiledTemplate(template_def)
                    self.templates[template_def.id] = compiled

                    # Index by normalized senders
                    for sender in template_def.senders:
                        norm_sender = normalize_sender(sender)
                        if norm_sender not in self.sender_index:
                            self.sender_index[norm_sender] = []
                        self.sender_index[norm_sender].append(compiled)

                    count += 1
            except Exception as e:
                logger.error(f"Failed to load templates from {yaml_file}: {e}")

        logger.info(f"Loaded {count} parser templates across {len(self.sender_index)} senders.")
        return count

    def get_templates_for_sender(self, sender: str) -> List[CompiledTemplate]:
        norm_sender = normalize_sender(sender)
        return self.sender_index.get(norm_sender, [])

    def get_all_templates(self) -> List[CompiledTemplate]:
        return list(self.templates.values())

    def sync_to_db(self, db: Session) -> int:
        """
        Seeds / updates all YAML templates into the SQLite parser_templates table.
        """
        synced_count = 0
        for template_id, compiled in self.templates.items():
            t_def = compiled.definition
            existing = db.query(ParserTemplateModel).filter(ParserTemplateModel.id == template_id).first()
            if existing:
                existing.issuer = t_def.issuer
                existing.card_type = t_def.card_type
                existing.senders_json = json.dumps([normalize_sender(s) for s in t_def.senders])
                existing.transaction_type = t_def.transaction_type
                existing.regex = t_def.regex
                existing.groups_json = json.dumps(t_def.groups)
                existing.category_override = t_def.category_override
                existing.is_active = True
            else:
                new_model = ParserTemplateModel(
                    id=template_id,
                    issuer=t_def.issuer,
                    card_type=t_def.card_type,
                    senders_json=json.dumps([normalize_sender(s) for s in t_def.senders]),
                    transaction_type=t_def.transaction_type,
                    regex=t_def.regex,
                    groups_json=json.dumps(t_def.groups),
                    category_override=t_def.category_override,
                    is_active=True,
                )
                db.add(new_model)
            synced_count += 1

        db.commit()
        logger.info(f"Synced {synced_count} templates to database.")
        return synced_count


# Global singleton registry instance
_registry_instance: Optional[TemplateRegistry] = None

def get_registry() -> TemplateRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TemplateRegistry()
    return _registry_instance
