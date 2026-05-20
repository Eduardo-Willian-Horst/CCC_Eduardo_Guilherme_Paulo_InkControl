"""Validacao compartilhada de upload de imagens."""

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def validate_uploaded_image(file_obj, field_name: str = "image") -> None:
    from studio.services.exceptions import ServiceValidationError

    if not file_obj:
        return
    if file_obj.size > MAX_IMAGE_BYTES:
        raise ServiceValidationError({field_name: "Arquivo muito grande (maximo 5MB)."})
    ctype = getattr(file_obj, "content_type", "") or ""
    if ctype and ctype not in ALLOWED_CONTENT_TYPES:
        name = (getattr(file_obj, "name", "") or "").lower()
        if not name.endswith(ALLOWED_EXTENSIONS):
            raise ServiceValidationError(
                {field_name: "Formato aceito: JPEG, PNG ou WebP."}
            )
