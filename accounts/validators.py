import os
from io import BytesIO
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

DANGEROUS_EXTENSIONS = {
    'html', 'htm', 'xhtml', 'svg', 'xml', 'js', 'json', 'php', 'phtml',
    'asp', 'aspx', 'jsp', 'py', 'sh', 'bat', 'cmd', 'ps1', 'exe', 'msi',
    'dll', 'com', 'scr', 'vbs', 'jar', 'cgi', 'pl'
}


def validate_file_size(file):
    if file.size > MAX_UPLOAD_SIZE:
        max_mb = MAX_UPLOAD_SIZE // (1024 * 1024)
        raise ValidationError(f"File size exceeds the maximum allowed limit of {max_mb} MB.")


def validate_image_file(file):
    if not file or not isinstance(file, UploadedFile):
        return

    validate_file_size(file)

    ext = os.path.splitext(file.name)[1].lower().lstrip('.')
    if ext in DANGEROUS_EXTENSIONS or ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '.{ext}'. Allowed formats for images are: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )

    # Verify actual image content with Pillow
    try:
        content = file.read()
        file.seek(0)
        img = Image.open(BytesIO(content))
        img.verify()
        if img.format not in ('JPEG', 'PNG'):
            raise ValidationError(
                f"Invalid image format '{img.format}'. Only genuine JPEG and PNG images are supported."
            )
    except ValidationError:
        raise
    except Exception:
        raise ValidationError("Uploaded file is not a valid or readable image.")


def validate_document_file(file):
    if not file or not isinstance(file, UploadedFile):
        return

    validate_file_size(file)

    ext = os.path.splitext(file.name)[1].lower().lstrip('.')
    if ext in DANGEROUS_EXTENSIONS or ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '.{ext}'. Allowed formats are: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}."
        )

    # Verify content based on extension
    content = file.read()
    file.seek(0)

    if ext == 'pdf':
        if not content.startswith(b'%PDF-'):
            raise ValidationError("Uploaded file has a .pdf extension but does not contain a valid PDF signature.")
    else:
        # Must be a valid JPEG or PNG image
        try:
            img = Image.open(BytesIO(content))
            img.verify()
            if img.format not in ('JPEG', 'PNG'):
                raise ValidationError(
                    f"Invalid image format '{img.format}'. Only genuine JPEG and PNG images are supported."
                )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError("Uploaded file is not a valid or readable document/image.")
