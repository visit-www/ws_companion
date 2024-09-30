from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from werkzeug.utils import secure_filename
from flask import redirect, url_for, flash, request,abort
from flask_login import current_user
import os
from . import db
from config import ANONYMOUS_USER_ID
import shutil
from datetime import datetime, timezone
from sqlalchemy import inspect

# ---------------------------------------------------------------
# * MyrModelView class for handling Admin-related tasks
# ---------------------------------------------------------------
class ExtendModelView(ModelView):
    # Display primary keys in the list view
    column_display_pk = True
    
    # Don't hide related fields from backrefs
    column_hide_backrefs = False
    @property
    def column_list(self):
        return self.scaffold_list_columns() + ['user_id','username']

    #column_list=['user_id','content_id','interaction_type','last_interaction','feedback','content_rating','time_spent','last_login']
    
class MyModelView(ModelView):
    # Display primary keys in the list view
    column_display_pk = True
    
    # Don't hide related fields from backrefs
    column_hide_backrefs = False
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    form_excluded_columns = ['filepath']

    form_overrides = {
        'file': FileUploadField
    }

    form_args = {
        'file': {
            'label': 'Select File',
            'base_path': os.path.join('dummy_folder'),
            'allow_overwrite': False,
            'allowed_extensions': ['txt', 'pdf', 'pptx', 'ppt', 'doc', 'xls', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 'pptx', 'html', 'md', 'mmd','svg','drawio','webp'],
        }
    }

    def custom_upload_file(self, form, model):
        category = model.category.value if hasattr(model.category, 'value') else model.category
        module = model.module.value if hasattr(model.module, 'value') else model.module
        filename = secure_filename(form.file.data.filename)
        uploaded_file = os.path.join('dummy_folder', filename)
        target_folder = os.path.join('files', category, module)
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(uploaded_file, target_folder)
        file_path = os.path.join(target_folder, filename)
        model.filepath = file_path

    def custom_delete_file(self, model):
        trash_folder = os.path.join('trash')
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        current_date_folder = os.path.join(trash_folder, date)
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

        try:
            if is_created:
                if upload_file:
                    self.custom_upload_file(form, model)
                    db.session.add(model)
                    db.session.commit()
                else:
                    db.session.add(model)
                    db.session.commit()
            else:
                file_present = bool(model.file)
                delete_file = '_file-delete' in request.form

                if file_present:
                    if os.path.exists(os.path.join('dummy_folder', model.file)):
                        if model.filepath:
                            orig_file_path = model.filepath
                            file_name = str(model.file)
                            trash_folder = os.path.join('trash')
                            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                            current_date_folder = os.path.join(trash_folder, date)
                            os.makedirs(current_date_folder, exist_ok=True)
                            shutil.move(orig_file_path, current_date_folder)
                            self.custom_upload_file(form, model)
                            db.session.add(model)
                            db.session.commit()
                        else:
                            self.custom_upload_file(form, model)
                            db.session.add(model)
                            db.session.commit()
                    else:
                        orig_file_path = model.filepath
                        file_name = str(model.file)
                        category = model.category.value if hasattr(model.category, 'value') else model.category
                        module = model.module.value if hasattr(model.module, 'value') else model.module
                        new_folder = os.path.join("files", category, module)
                        new_file_path = os.path.join(new_folder, file_name)
                        os.makedirs(new_folder, exist_ok=True)
                        if orig_file_path != new_file_path:
                            shutil.move(orig_file_path, new_folder)
                            file_path = os.path.join(new_folder, file_name)
                            model.filepath = file_path
                            db.session.add(model)
                            db.session.commit()
                        else:
                            db.session.add(model)
                            db.session.commit()
                else:
                    if delete_file:
                        self.custom_delete_file(model)
                        db.session.add(model)
                        db.session.commit()
                    else:
                        db.session.add(model)
                        db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during the update: {e}", 'danger')

    def on_model_delete(self, model):
        self.custom_delete_file(model)
        db.session.delete(model)
        db.session.commit()

# ---------------------------------------------------------------
from .models import User
from config import userdir, basedir
import json
from sqlalchemy.inspection import inspect 
class UserModelView(ModelView):
    # Display primary keys in the list view
    column_display_pk = True
    
    # Don't hide related fields from backrefs
    column_hide_backrefs = False

    def is_accessible(self):
        # Check if the current user is authenticated and an admin
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    def serialize_model(self, instance):
        """Serializes a SQLAlchemy model instance to a dictionary."""
        return {c.key: getattr(instance, c.key) for c in inspect(instance).mapper.column_attrs}

    def custom_user_delete(self, model):
        try:
            # Ensure the model is a User instance
            if isinstance(model, User):
                user_id = model.id
                username = model.username

                # Prevent deletion of admin or anonymous user
                if user_id == ANONYMOUS_USER_ID or username == 'admin':
                    flash("DELETING ANONYMOUS_USER or ADMIN IS ALLOWED ONLY THROUGH DATABASE SHELL", "warning")
                    raise ValueError("You should delete all foreign key records related to anonymous user before deletion.")
                
                # Archive user's profile picture, if it exists
                profile_pic_path = model.profile.profile_pic_path if model.profile else None
                if profile_pic_path and os.path.exists(profile_pic_path):
                    archived_pic_folder = os.path.join('archived', f"{user_id}", 'profile_pic')
                    os.makedirs(archived_pic_folder, exist_ok=True)
                    if "dummy" not in profile_pic_path:
                        shutil.move(profile_pic_path, archived_pic_folder)

                # Archive user metadata
                user_metadata = {
                    "user": self.serialize_model(model),
                    "profile": self.serialize_model(model.profile) if model.profile else None,
                    "user_data": [self.serialize_model(data) for data in model.user_data.all()],
                    "user_content_states": [self.serialize_model(state) for state in model.user_content_states.all()],
                    "report_templates": [self.serialize_model(template) for template in model.report_templates],
                    "feedbacks": [self.serialize_model(feedback) for feedback in model.feedbacks]
                }
                
                # Save metadata as a JSON file
                archived_metadata_folder = os.path.join('archived', f"{user_id}", 'meta_data')
                os.makedirs(archived_metadata_folder, exist_ok=True)
                metadata_file_path = os.path.join(archived_metadata_folder, f"user_{user_id}_metadata.json")
                
                with open(metadata_file_path, 'w') as metadata_file:
                    json.dump(user_metadata, metadata_file, indent=4, default=str)

                # Remove the user's directory from user_data
                old_user_dir = os.path.join(userdir, f"{user_id}")
                if os.path.exists(old_user_dir):
                    shutil.rmtree(old_user_dir)
        except OSError as e:
            flash(f'Error during user deletion: {str(e)}', 'danger')
            print(f'Error during user deletion: {str(e)}')

    def on_model_delete(self, model):
        self.custom_user_delete(model)  # Archive and clean up before deletion
        db.session.delete(model)
        db.session.commit()