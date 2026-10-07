from typing import Annotated

from fastapi import Depends, Request

from core.services.application import ApplicationServices
from core.services.strapi import StrapiService


def get_application_services(request: Request) -> ApplicationServices:
    return request.app.state.services


ApplicationServicesDependency = Annotated[ApplicationServices, Depends(get_application_services)]


def get_strapi(services: ApplicationServicesDependency) -> StrapiService:
    return services.strapi


StrapiDependency = Annotated[StrapiService, Depends(get_strapi)]