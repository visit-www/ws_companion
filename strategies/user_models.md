Here's the detailed table for the **User** model included with the other models, showing fields, data types, foreign keys, and default values:

### 1. **User Model (`users` table)**
| Field         | Data Type      | Foreign Key | Default Value               |
|---------------|----------------|-------------|-----------------------------|
| id            | Integer        | None        | Auto-increment              |
| username      | String(150)    | None        | None                        |
| password      | String(150)    | None        | None                        |
| email         | String(150)    | None        | None                        |
| is_paid       | Boolean        | None        | False                       |
| is_admin      | Boolean        | None        | False                       |
| status        | String(50)     | None        | 'active'                    |
| created_at    | DateTime       | None        | Current UTC datetime        |
| last_updated  | DateTime       | None        | Current UTC datetime, on update |

### 2. **UserData Model (`user_data` table)**
| Field            | Data Type        | Foreign Key          | Default Value               |
|------------------|------------------|----------------------|-----------------------------|
| id               | Integer          | None                 | Auto-increment              |
| user_id          | Integer          | `users.id`           | None                        |
| content_id       | Integer          | `contents.id`        | None                        |
| interaction_type | Enum             | None                 | 'viewed'                    |
| interaction_date | DateTime         | None                 | Current UTC datetime        |
| feedback         | Text             | None                 | None                        |
| content_rating   | Integer          | None                 | None                        |
| time_spent       | Integer          | None                 | 0                           |
| last_interaction | DateTime         | None                 | None                        |

### 3. **UserProfile Model (`user_profiles` table)**
| Field             | Data Type        | Foreign Key        | Default Value                  |
|-------------------|------------------|--------------------|---------------------------------|
| id                | Integer          | None               | Auto-increment                 |
| user_id           | Integer          | `users.id`         | None                           |
| profile_pic       | String(255)      | None               | 'dummy_profile_pic.png'        |
| profile_pic_path  | String(255)      | None               | 'static/assets/images/dummy_profile_pic.png' |
| preferred_categories | Text         | None               | All categories as JSON         |
| preferred_modules | Text             | None               | All modules as JSON            |
| report_templates  | Text             | None               | None                           |
| created_at        | DateTime         | None               | Current UTC datetime           |
| updated_at        | DateTime         | None               | Current UTC datetime, on update|

### 4. **UserContentState Model (`user_content_states` table)**
| Field             | Data Type        | Foreign Key        | Default Value                  |
|-------------------|------------------|--------------------|---------------------------------|
| id                | Integer          | None               | Auto-increment                 |
| user_id           | Integer          | `users.id`         | None                           |
| content_id        | Integer          | `contents.id`      | None                           |
| modified_file_path| String(255)      | None               | None                           |
| annotations       | Text             | None               | None                           |
| created_at        | DateTime         | None               | Current UTC datetime           |
| updated_at        | DateTime         | None               | Current UTC datetime, on update|

### 5. **UserReportTemplate Model (`user_report_templates` table)**
| Field             | Data Type        | Foreign Key        | Default Value                  |
|-------------------|------------------|--------------------|---------------------------------|
| id                | Integer          | None               | Auto-increment                 |
| body_part         | Enum             | None               | None                           |
| modality          | Enum             | None               | None                           |
| template_name     | String(255)      | None               | None                           |
| tags              | Text             | None               | None                           |
| is_public         | Boolean          | None               | False                          |
| user_id           | Integer          | `users.id`         | None                           |
| category          | Enum             | None               | None                           |
| module            | Enum             | None               | None                           |
| template_text     | Text             | None               | None                           |
| file              | String(255)      | None               | None                           |
| file_path         | String(255)      | None               | None                           |
| created_at        | DateTime         | None               | Current UTC datetime           |
| updated_at        | DateTime         | None               | Current UTC datetime, on update|

### 6. **UserFeedback Model (`user_feedbacks` table)**
| Field             | Data Type        | Foreign Key        | Default Value                  |
|-------------------|------------------|--------------------|---------------------------------|
| id                | Integer          | None               | Auto-increment                 |
| user_id           | Integer          | `users.id`         | None                           |
| content_id        | Integer          | `contents.id`      | None                           |
| feedback          | Text             | None               | None                           |
| is_public         | Boolean          | None               | False                          |
| user_display_name | String(100)      | None               | None                           |

These tables include the key fields, data types, foreign keys, and default values for each model in your application. This comprehensive overview should help you plan the updates needed for the login route and ensure all relevant data is accurately managed across the user data models. Let me know how you'd like to proceed!
