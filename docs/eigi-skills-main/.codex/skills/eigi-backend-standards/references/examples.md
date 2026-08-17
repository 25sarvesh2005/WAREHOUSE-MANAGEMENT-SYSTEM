# Eigi Backend Examples

Use these examples as starting templates for new backend modules. They are based on Vaani Core patterns from `user_router.py`, `user_controller.py`, `user_crud.py`, and `core/services/mcp/service.py`.

## Router Example

Use this shape for authenticated FastAPI endpoints. Keep the route thin: parse request data, decode auth, check active status if local code does that in routes, call the controller, and handle route-level errors.

```python
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from commons.auth import decodeJWT
from core import logger
from core.apis.schemas.requests.resource_request import ResourceCreate
from core.apis.schemas.responses.resource_response import ResourceResponse
from core.controllers.resource_controller import ResourceController

resource_router = APIRouter()
logging = logger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


@resource_router.post(
    "/v1/resources",
    status_code=status.HTTP_201_CREATED,
    response_model=ResourceResponse,
)
async def create_resource(
    request: ResourceCreate,
    token: str = Depends(oauth2_scheme),
):
    """
    Create a resource for the authenticated user.

    Creates a resource after validating the bearer token and active user status.
    Domain-specific ownership and business validation are handled by the controller.

    Args:
        request (ResourceCreate): Resource creation payload.
        token (str): OAuth2 bearer token for authentication.

    Returns:
        ResourceResponse: Created resource details.

    Raises:
        HTTPException 401: Invalid or expired authentication token.
        HTTPException 403: User account is not ACTIVE.
        HTTPException 400: Invalid resource data or duplicate resource.
        HTTPException 500: Internal server error.
    """
    try:
        logging.info("Calling POST /v1/resources endpoint")
        authenticated_user_details = decodeJWT(token=token)
        if not authenticated_user_details:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        if authenticated_user_details.get("status") != "ACTIVE":
            logging.warning(
                f"User with email {authenticated_user_details.get('email')} is not active"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not active",
            )

        response = await ResourceController().create_resource(
            resource_data=request.model_dump(),
            authenticated_user_details=authenticated_user_details,
        )
        return ResourceResponse(**response)
    except HTTPException as httperror:
        logging.error(f"Error in POST /v1/resources endpoint: {httperror}")
        raise httperror
    except Exception as error:
        logging.error(f"Error in POST /v1/resources endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
```

For internal service-to-service routes, follow nearby internal routes: omit user auth only when the existing service explicitly does so, document that the route is internal, and still log and convert unexpected errors to 500.

## Controller Example

Use this shape for business orchestration. Instantiate the CRUD/services in `__init__`, log method entry, use warnings for expected business rejections, raise meaningful `HTTPException`s, and convert unexpected failures consistently.

```python
from fastapi import HTTPException, status

from core import logger
from core.cruds.resource_crud import CRUDResource

logging = logger(__name__)


class ResourceController:
    def __init__(self):
        self.CRUDResource = CRUDResource()

    async def create_resource(
        self,
        resource_data: dict,
        authenticated_user_details: dict,
    ) -> dict:
        """
        Create a resource for the authenticated user.

        Args:
            resource_data: Resource creation data.
            authenticated_user_details: Authenticated user information.

        Returns:
            dict: Created resource response payload.

        Raises:
            HTTPException: If a duplicate resource exists or creation fails.
        """
        try:
            logging.info("Executing ResourceController.create_resource")
            user_id = authenticated_user_details.get("id")

            existing_resource = await self.CRUDResource.get_by_name(
                user_id=user_id,
                name=resource_data.get("name", ""),
            )
            if existing_resource:
                logging.warning(
                    f"Resource with name {resource_data.get('name')} already exists"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Resource with this name already exists",
                )

            resource_data["user_id"] = user_id
            resource = await self.CRUDResource.create(obj_in=resource_data)
            if not resource:
                logging.error("Failed to create resource")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create resource",
                )

            logging.info(f"Resource created successfully: {resource['id']}")
            return {
                "id": str(resource["id"]),
                "name": resource["name"],
                "status": resource["status"],
                "created_at": resource["created_at"],
            }
        except HTTPException:
            raise
        except Exception as error:
            logging.error(f"Error in ResourceController.create_resource: {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error",
            )
```

Use this pattern for lookup and ownership checks:

```python
resource = await self.CRUDResource.get_by_id(id=resource_id)
if not resource:
    logging.warning(f"Resource not found: {resource_id}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Resource not found",
    )

if str(resource["user_id"]) != authenticated_user_details.get("id"):
    logging.warning(
        f"User {authenticated_user_details.get('id')} cannot access resource {resource_id}"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have access to this resource",
    )
```

## CRUD Example

Use this shape for repository/persistence classes. Keep the class focused on database operations and leave business rules to controllers. The CRUD class should get the database/session helper from `database.py` or the local equivalent instead of requiring route/controller methods to pass `db`.

```python
from datetime import datetime
from pytz import timezone

from core import logger
from core.database.database import session
from core.models.resource_model import Resource
from core.utils.custom.database_helper import to_dict

logging = logger(__name__)


class CRUDResource:
    """Database access layer for resource records."""

    async def create(self, *, obj_in: dict) -> dict:
        """
        Create a new resource record.

        Args:
            obj_in: Resource creation data.

        Returns:
            dict: Created resource record.

        Raises:
            Exception: If the database write fails.
        """
        try:
            logging.info("Executing CRUDResource.create")
            resource_data = dict(obj_in)
            timestamp = datetime.now(timezone("UTC")).strftime("%Y-%m-%d %H:%M:%S.%f")
            resource_data.update(
                {
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )

            resource = Resource(**resource_data)
            with session() as transaction_session:
                transaction_session.add(resource)
                transaction_session.commit()
                transaction_session.refresh(resource)

            return to_dict(resource)
        except Exception as error:
            logging.error(f"Error in CRUDResource.create function: {error}")
            raise error

    async def get_by_id(self, *, id: str) -> dict | None:
        """
        Read a resource record by unique ID.

        Args:
            id: Resource ID.

        Returns:
            dict | None: Resource record if found, otherwise None.

        Raises:
            Exception: If the database read fails.
        """
        try:
            logging.info("Executing CRUDResource.get_by_id")
            with session() as transaction_session:
                resource = (
                    transaction_session.query(Resource)
                    .filter(Resource.id == id)
                    .first()
                )

            if resource:
                return to_dict(resource)

            logging.warning(f"No resource found with id: {id}")
            return None
        except Exception as error:
            logging.error(f"Error in CRUDResource.get_by_id function: {error}")
            raise error

    async def get_by_name(
        self,
        *,
        user_id: str,
        name: str,
    ) -> dict | None:
        """
        Read a resource by owner and name for duplicate checks.

        Args:
            user_id: Owner user ID.
            name: Resource name.

        Returns:
            dict | None: Resource record if found, otherwise None.

        Raises:
            Exception: If the database read fails.
        """
        try:
            logging.info("Executing CRUDResource.get_by_name")
            with session() as transaction_session:
                resource = (
                    transaction_session.query(Resource)
                    .filter(Resource.user_id == user_id, Resource.name == name)
                    .first()
                )

            return to_dict(resource) if resource else None
        except Exception as error:
            logging.error(f"Error in CRUDResource.get_by_name function: {error}")
            raise error

    async def update(self, *, id: str, obj_in: dict) -> dict | None:
        """
        Update a resource record by unique ID.

        Args:
            id: Resource ID.
            obj_in: Resource update data.

        Returns:
            dict | None: Updated resource record if found, otherwise None.

        Raises:
            Exception: If the database update fails.
        """
        try:
            logging.info("Executing CRUDResource.update")
            with session() as transaction_session:
                resource = (
                    transaction_session.query(Resource)
                    .filter(Resource.id == id)
                    .first()
                )
                if resource is None:
                    logging.warning(f"No resource found with id: {id}")
                    return None

                for field, value in obj_in.items():
                    setattr(resource, field, value)
                resource.updated_at = datetime.now(timezone("UTC")).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
                transaction_session.commit()
                transaction_session.refresh(resource)

            return to_dict(resource)
        except Exception as error:
            logging.error(f"Error in CRUDResource.update function: {error}")
            raise error
```

## Service Example

Use services for external clients, providers, connection state, validation workflows, cleanup, and reusable domain operations. The MCP service pattern is a good example: a service wraps a lower-level client, logs lifecycle methods, and exposes a clean public API.

For normal service operations, log failures and re-raise so the controller/router can preserve the correct HTTP behavior. Return structured failure dictionaries only when the method's explicit contract is a validation/status/tool-result payload, such as MCP connection validation returning `is_valid: False`.

```python
from typing import Any, Dict, Optional

from core import logger
from core.apis.schemas.requests.resource_request import ResourceProviderRequest
from core.services.resource.client import ResourceClient, get_resource_client

logging = logger(__name__)


class ResourceConnectionService:
    """Resource connection service for provider operations.

    This service provides a clean interface for managing provider connections,
    abstracting away the underlying client implementation details.

    Usage:
        service = get_resource_connection_service()
        await service.start_connection(request, user_id)
        result = await service.call_provider(resource_id, payload)
        await service.stop_connection(resource_id, user_id)
    """

    def __init__(self):
        """Initialize the resource connection service."""
        logging.info("Executing ResourceConnectionService.__init__ function")
        self._client: ResourceClient = get_resource_client()
        logging.info("ResourceConnectionService initialized successfully")

    @property
    def client(self) -> ResourceClient:
        """Get the underlying resource client."""
        return self._client

    async def start_connection(
        self,
        provider_request: ResourceProviderRequest,
        user_id: str,
    ) -> bool:
        """Start or join a provider connection.

        Args:
            provider_request: Provider connection configuration.
            user_id: User ID requesting the connection.

        Returns:
            True if successful, False otherwise.
        """
        logging.info("Executing ResourceConnectionService.start_connection function")
        logging.debug(
            f"Starting provider connection '{provider_request.name}' for user {user_id}"
        )
        return await self._client.start_connection(provider_request, user_id)

    async def call_provider(self, resource_id: str, payload: Dict[str, Any]) -> Any:
        """Call the provider for a resource.

        Args:
            resource_id: Resource connection ID.
            payload: Provider request payload.

        Returns:
            Provider result.

        Raises:
            Exception: If the provider call fails.
        """
        logging.info("Executing ResourceConnectionService.call_provider function")
        logging.debug(f"Calling provider for resource: {resource_id}")
        try:
            result = await self._client.call(resource_id, payload)
            logging.info(f"Provider call completed successfully: {resource_id}")
            return result
        except Exception as error:
            logging.error(f"Error in ResourceConnectionService.call_provider: {error}")
            raise error

    async def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate provider configuration.

        Args:
            config: Provider configuration data.

        Returns:
            Dict with validation status and provider metadata.
        """
        logging.info("Executing ResourceConnectionService.validate_config function")
        logging.debug(f"Validating provider config for '{config.get('name', 'unknown')}'")
        try:
            metadata = await self._client.validate(config)
            logging.info(
                f"Provider config validation successful for '{config.get('name')}'"
            )
            return {
                "is_valid": True,
                "metadata": metadata,
                "error": None,
            }
        except Exception as error:
            logging.error(
                f"Error in ResourceConnectionService.validate_config: {error}"
            )
            return {
                "is_valid": False,
                "metadata": {},
                "error": "Provider configuration validation failed",
            }
```

Use a singleton accessor when the service owns shared connection state or an expensive reusable client:

```python
_resource_service_instance: Optional[ResourceConnectionService] = None


def get_resource_connection_service() -> ResourceConnectionService:
    """Get or create the global resource connection service instance."""
    global _resource_service_instance
    if _resource_service_instance is None:
        _resource_service_instance = ResourceConnectionService()
    return _resource_service_instance
```

Do not use a singleton for simple stateless helper logic unless the surrounding repo already follows that pattern.
