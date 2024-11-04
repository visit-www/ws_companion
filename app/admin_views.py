from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from flask import redirect, url_for, flash, request
from flask_login import current_user
from wtforms_sqlalchemy.fields import QuerySelectField
from werkzeug.utils import secure_filename
import os
import shutil
import json
from datetime import datetime, timezone
from sqlalchemy import inspect, or_

from . import db
from .models import Content, Reference, User
from config import ANONYMOUS_USER_ID, userdir

# ExtendModelView class for general model handling
class ExtendModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False

    @property
    def column_list(self):
        return self.scaffold_list_columns() + ['user_id', 'username']

from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from werkzeug.utils import secure_filename
from flask import flash, redirect, url_for
from flask_login import current_user
import os
import shutil
from datetime import datetime, timezone
from . import db

class MyModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    form_excluded_columns = ['filepath']
    form_overrides = {'file': FileUploadField}
    form_args = {
        'file': {
            'label': 'Select File',
            'base_path': os.path.join('dummy_folder'),
            'allow_overwrite': False,
            'allowed_extensions': [
                'txt', 'pdf', 'pptx', 'ppt', 'doc', 'xls', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 
                'html', 'md', 'mmd', 'svg', 'drawio', 'webp'
            ],
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    def custom_upload_file(self, form, model):
        category = model.category.value if hasattr(model.category, 'value') else model.category
        module = model.module.value if hasattr(model.module, 'value') else model.module
        filename = secure_filename(form.file.data.filename)
        uploaded_file = os.path.join('dummy_folder', filename)
        target_folder = os.path.join('files', category, module)
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(uploaded_file, target_folder)
        model.filepath = os.path.join(target_folder, filename)

    def custom_delete_file(self, model):
        trash_folder = 'trash'
        date_folder = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        current_date_folder = os.path.join(trash_folder, date_folder)
        os.makedirs(current_date_folder, exist_ok=True)

        if model.filepath and os.path.exists(model.filepath):
            try:
                shutil.move(model.filepath, current_date_folder)
                model.filepath = None
                model.file = None
            except OSError as e:
                flash(f'Error deleting file: {str(e)}', 'danger')

    def on_model_change(self, form, model, is_created):
        upload_file = bool(form.file.data)
        old_category = model.category if not is_created else None
        old_module = model.module if not is_created else None
        original_filepath = model.filepath  # Store the original file path for reference

        try:
            # Check if a new file is being uploaded on creation
            if is_created and upload_file:
                self.custom_upload_file(form, model)
            else:
                # If the category or module has changed, move the file to the new directory
                if not is_created and (old_category != model.category or old_module != model.module) and original_filepath:
                    # Determine the new directory based on updated category and module
                    new_category = model.category.value if hasattr(model.category, 'value') else model.category
                    new_module = model.module.value if hasattr(model.module, 'value') else model.module
                    new_folder = os.path.join('files', new_category, new_module)
                    os.makedirs(new_folder, exist_ok=True)

                    # Move the file to the new folder
                    filename = os.path.basename(original_filepath)
                    new_filepath = os.path.join(new_folder, filename)
                    shutil.move(original_filepath, new_filepath)
                    model.filepath = new_filepath  # Update the model's filepath

                    flash(f"File moved to the new category/module folder: {new_category}/{new_module}", 'success')

            db.session.add(model)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during the update: {e}", 'danger')

    def on_model_delete(self, model):
        self.custom_delete_file(model)
        db.session.delete(model)
        db.session.commit()



# Custom User Model View for handling specific user-related admin tasks
class UserModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    def serialize_model(self, instance):
        return {c.key: getattr(instance, c.key) for c in inspect(instance).mapper.column_attrs}

    def custom_user_delete(self, model):
        if isinstance(model, User):
            user_id = model.id
            if user_id == ANONYMOUS_USER_ID or model.username == 'admin':
                flash("Deleting the anonymous user or admin is restricted.", "warning")
                return

            # Archive metadata and delete user files
            user_metadata = {
                "user": self.serialize_model(model),
                "profile": self.serialize_model(model.profile) if model.profile else None,
            }
            metadata_file_path = os.path.join('archived', f"user_{user_id}_metadata.json")
            os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)
            with open(metadata_file_path, 'w') as f:
                json.dump(user_metadata, f, indent=4, default=str)

            user_dir = os.path.join(userdir, f"{user_id}")
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)

    def on_model_delete(self, model):
        self.custom_user_delete(model)
        db.session.delete(model)
        db.session.commit()


class ReferenceAdmin(ModelView):
    # Define form columns to include content title instead of content_id
    form_columns = ['title', 'category', 'module', 'content_id', 'file', 'filepath', 'url', 'embed_code', 'description']

    # Override form fields
    form_overrides = {
        'content_id': QuerySelectField,  # Display Content titles in dropdown
        'file': FileUploadField
    }
    form_args = {
        'content_id': {
            'query_factory': lambda: db.session.query(Content),  # Query Content model for dropdown
            'get_label': 'title'  # Show Content title in dropdown instead of ID
        },
        'file': {
            'label': 'Select File',
            'base_path': os.path.join('dummy_folder'),  # Adjust to the correct folder path for uploads
            'allow_overwrite': False,
            'allowed_extensions': [
                'txt', 'pdf', 'pptx', 'ppt', 'doc', 'xls', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 
                'html', 'md', 'mmd', 'svg', 'drawio', 'webp'
            ],
        }
    }

    # Custom column list for easy viewing
    column_list = ('title', 'category', 'module', 'content_id')
    column_labels = {'content_id': 'Select Content title'}

    # Custom file upload handler
    def custom_upload_file(self, form, model):
        category = model.category.value if hasattr(model.category, 'value') else model.category
        module = model.module.value if hasattr(model.module, 'value') else model.module
        filename = secure_filename(form.file.data.filename)
        uploaded_file = os.path.join('dummy_folder', filename)
        target_folder = os.path.join('files', category, module)
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(uploaded_file, target_folder)
        model.filepath = os.path.join(target_folder, filename)

    # Handle file deletion by moving files to a trash folder
    def custom_delete_file(self, model):
        trash_folder = 'trash'
        date_folder = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        current_date_folder = os.path.join(trash_folder, date_folder)
        os.makedirs(current_date_folder, exist_ok=True)

        if model.filepath and os.path.exists(model.filepath):
            try:
                shutil.move(model.filepath, current_date_folder)
                model.filepath = None
                model.file = None
            except OSError as e:
                flash(f'Error deleting file: {str(e)}', 'danger')

    # Override on_model_change to set content_id based on content_title selection
    def on_model_change(self, form, model, is_created):
        # Set content_id based on the selected content_title
        if form.content_id.data:
            selected_content = form.content_id.data
            model.content_id = selected_content.id

        # Handle file upload if file data is provided
        if form.file.data:
            self.custom_upload_file(form, model)

        db.session.add(model)
        db.session.commit()

    # Override on_model_delete to handle file deletion on model delete
    def on_model_delete(self, model):
        self.custom_delete_file(model)  # Delete file if model is deleted
        db.session.delete(model)
        db.session.commit()