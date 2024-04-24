from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from danswer.auth.users import current_admin_user
from danswer.auth.users import current_user
from danswer.configs.model_configs import GEN_AI_MODEL_PROVIDER
from danswer.db.chat import get_persona_by_id
from danswer.db.chat import get_personas
from danswer.db.chat import mark_persona_as_deleted
from danswer.db.chat import update_all_personas_display_priority
from danswer.db.chat import update_persona_visibility
from danswer.db.engine import get_session
from danswer.db.models import User
from danswer.db.persona import create_update_persona
from danswer.llm.answering.prompts.utils import build_dummy_prompt
from danswer.llm.utils import get_default_llm_version
from danswer.server.features.persona.models import CreatePersonaRequest
from danswer.server.features.persona.models import PersonaSnapshot
from danswer.server.features.persona.models import PromptTemplateResponse
from danswer.utils.logger import setup_logger

logger = setup_logger()


admin_router = APIRouter(prefix="/admin/persona")
basic_router = APIRouter(prefix="/persona")


@admin_router.post("")
def create_persona(
    create_persona_request: CreatePersonaRequest,
    user: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> PersonaSnapshot:
    return create_update_persona(
        persona_id=None,
        create_persona_request=create_persona_request,
        user=user,
        db_session=db_session,
    )


@admin_router.patch("/{persona_id}")
def update_persona(
    persona_id: int,
    update_persona_request: CreatePersonaRequest,
    user: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> PersonaSnapshot:
    return create_update_persona(
        persona_id=persona_id,
        create_persona_request=update_persona_request,
        user=user,
        db_session=db_session,
    )


class IsVisibleRequest(BaseModel):
    is_visible: bool


@admin_router.patch("/{persona_id}/visible")
def patch_persona_visibility(
    persona_id: int,
    is_visible_request: IsVisibleRequest,
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_persona_visibility(
        persona_id=persona_id,
        is_visible=is_visible_request.is_visible,
        db_session=db_session,
    )


class DisplayPriorityRequest(BaseModel):
    # maps persona id to display priority
    display_priority_map: dict[int, int]


@admin_router.put("/display-priority")
def patch_persona_display_priority(
    display_priority_request: DisplayPriorityRequest,
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    update_all_personas_display_priority(
        display_priority_map=display_priority_request.display_priority_map,
        db_session=db_session,
    )


@admin_router.delete("/{persona_id}")
def delete_persona(
    persona_id: int,
    user: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    mark_persona_as_deleted(
        persona_id=persona_id,
        user_id=user.id if user is not None else None,
        db_session=db_session,
    )


@admin_router.get("")
def list_personas_admin(
    _: User | None = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = False,
) -> list[PersonaSnapshot]:
    return [
        PersonaSnapshot.from_model(persona)
        for persona in get_personas(
            db_session=db_session,
            user_id=None,  # user_id = None -> give back all personas
            include_deleted=include_deleted,
        )
    ]


"""Endpoints for all"""


@basic_router.get("")
def list_personas(
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
    include_deleted: bool = False,
) -> list[PersonaSnapshot]:
    user_id = user.id if user is not None else None
    return [
        PersonaSnapshot.from_model(persona)
        for persona in get_personas(
            user_id=user_id, include_deleted=include_deleted, db_session=db_session
        )
    ]

@basic_router.get("/default-model")
def default_model(
    _: User | None = Depends(current_user),
) -> str:
    return get_default_llm_version()[0]


@basic_router.get("/{persona_id}")
def get_persona(
    persona_id: int,
    user: User | None = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> PersonaSnapshot:
    return PersonaSnapshot.from_model(
        get_persona_by_id(
            persona_id=persona_id,
            user_id=user.id if user is not None else None,
            db_session=db_session,
        )
    )


@basic_router.get("/utils/prompt-explorer")
def build_final_template_prompt(
    system_prompt: str,
    task_prompt: str,
    retrieval_disabled: bool = False,
    _: User | None = Depends(current_user),
) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        final_prompt_template=build_dummy_prompt(
            system_prompt=system_prompt,
            task_prompt=task_prompt,
            retrieval_disabled=retrieval_disabled,
        )
    )


"""Utility endpoints for selecting which model to use for a persona.
Putting here for now, since we have no other flows which use this."""

GPT_4_MODEL_VERSIONS = [
    "gpt-4",
    "gpt-4-turbo-preview",
    "gpt-4-1106-preview",
    "gpt-4-32k",
    "gpt-4-0613",
    "gpt-4-32k-0613",
    "gpt-4-0314",
    "gpt-4-32k-0314",
]
GPT_3_5_TURBO_MODEL_VERSIONS = [
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k-0613",
    "gpt-3.5-turbo-0301",
]


@admin_router.get("/utils/list-available-models")
def list_available_model_versions(
    _: User | None = Depends(current_admin_user),
) -> list[str]:
    # currently only support selecting different models for OpenAI
    if GEN_AI_MODEL_PROVIDER != "openai":
        return []

    return GPT_4_MODEL_VERSIONS + GPT_3_5_TURBO_MODEL_VERSIONS


@admin_router.get("/utils/default-model")
def get_default_model(
    _: User | None = Depends(current_admin_user),
) -> str:
    # currently only support selecting different models for OpenAI
    if GEN_AI_MODEL_PROVIDER != "openai":
        return ""

    return get_default_llm_version()[0]
