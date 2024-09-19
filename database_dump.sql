PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version VALUES('6777b679ef70');
CREATE TABLE IF NOT EXISTS "contents" (
	id INTEGER NOT NULL, 
	filepath VARCHAR(255), 
	title VARCHAR(565) NOT NULL, 
	category VARCHAR(22) NOT NULL, 
	module VARCHAR(16) NOT NULL, 
	status VARCHAR(9), 
	external_url VARCHAR(2083), 
	embed_code TEXT, 
	keywords TEXT, 
	language VARCHAR(20), 
	content_tags TEXT, 
	importance_level VARCHAR(6), 
	featured BOOLEAN, 
	paid_access BOOLEAN, 
	api_endpoint VARCHAR(2083), 
	description TEXT, 
	version FLOAT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	last_accessed DATETIME, 
	access_count INTEGER, 
	view_duration INTEGER, 
	usage_statistics TEXT, 
	created_by VARCHAR(80), 
	file_path VARCHAR(255), 
	file_size INTEGER, 
	estimated_reading_time INTEGER, 
	bookmark_count INTEGER, 
	related_content TEXT, 
	related_api_links TEXT, 
	accessibility_features TEXT, 
	file VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO contents VALUES(1,'files/CLASSIFICATIONS/CHEST/2015-Clinical_value_of_relative_quantification_ultrasound_elastography_-_Fausto.pdf','update file without checking delete box','CLASSIFICATIONS','CHEST','PUBLISHED',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',2.0,'2024-09-04 20:42:12.000000','2024-09-04 20:46:06.252535',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','2015-Clinical_value_of_relative_quantification_ultrasound_elastography_-_Fausto.pdf');
INSERT INTO contents VALUES(2,'files/GUIDELINES/GASTROINTESTINAL/Cyst_Pathway_Version_1_Dec_2018-2_copy_3_1.pdf','Pancreatic cyst pathways','GUIDELINES','GASTROINTESTINAL','PUBLISHED',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to CLASSIFICATIONS and the module name is CHEST',1.300000000000000044,'2024-09-04 20:52:35.000000','2024-09-04 21:01:02.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','Cyst_Pathway_Version_1_Dec_2018-2_copy_3_1.pdf');
INSERT INTO contents VALUES(3,NULL,'URL test','GUIDELINES','HEAD_AND_NECK','DRAFT','https://youtu.be/O7kSYIuFC90?feature=shared','','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-06 21:24:12.000000','2024-09-06 21:24:12.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(4,NULL,'Embed YouTube video','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<iframe width="560" height="315" src="https://www.youtube.com/embed/O7kSYIuFC90?si=X-55zjPakp7MXJg6" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.199999999999999956,'2024-09-06 21:24:12.000000','2024-09-06 21:24:12.517103',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(5,'files/DIFFERENTIAL_DIAGNOSIS/HEAD_AND_NECK/Brain_death_diagnosis.docx','Test content to another category','DIFFERENTIAL_DIAGNOSIS','HEAD_AND_NECK','DRAFT',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to DIFFERENTIAL_DIAGNOSIS and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 18:17:08.000000','2024-09-07 18:17:08.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','Brain_death_diagnosis.docx');
INSERT INTO contents VALUES(6,NULL,'Embed video from YouTube','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: 56.25%;"><iframe src="https://www.youtube.com/embed/q3lX2p_Uy9I?rel=0" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen scrolling="no" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share;"></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(7,NULL,'figma embed','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 450px; position: relative;"><iframe src="https://www.figma.com/embed?node-id=0%3A286&url=https%3A%2F%2Fwww.figma.com%2Ffile%2FzCl6dPZyG0DWoIOvetwBMG%2FFigma-Basics%3Fnode-id%3D0%253A286&embed_host=iframely" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(8,NULL,'google callender','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: 75%;"><iframe src="https://calendar.google.com/calendar/embed?src=iframely.embeds%40gmail.com" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(9,NULL,'imdb embed','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: 56.25%;"><iframe src="https://www.imdb.com/videoembed/vi2025309977" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen scrolling="no" allow="encrypted-media;"></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(10,NULL,'flicker images ','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<a data-flickr-embed="true" href="https://www.flickr.com/photos/9somboon/35071348993/" title="Big Yor at PakPra Thailand by Somboon Kaeoboonsong, on Flickr"><img src="https://live.staticflickr.com/4205/35071348993_39e6733199_b.jpg" width="100%" alt="Big Yor at PakPra Thailand"></a><script async src="https://embedr.flickr.com/assets/client-code.js" charset="utf-8"></script>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(11,NULL,'you form embedded','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 600px; position: relative;"><iframe src="https://app.youform.com/forms/xrjcjyti" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(13,NULL,'vim video embedded','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: 56.338%;"><iframe src="https://player.vimeo.com/video/783455878?app_id=122963&byline=0&badge=0&portrait=0&title=0" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen scrolling="no" allow="encrypted-media;"></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(14,NULL,'canva embedded','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: 56.25%;"><iframe src="https://www.canva.com/design/DACHZTlgWkU/view?embed&meta" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen allow="fullscreen;"></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(15,NULL,'google doc embedded','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 0; position: relative; padding-bottom: 129.4118%;"><iframe src="https://docs.google.com/document/d/1dZ38Ohz-wLyBBAuOXlWRyIo9hB-n3NVRtGzzM8VG1es/preview?usp=embed_googleplus" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 19:43:56.000000','2024-09-07 19:43:56.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(16,NULL,'YouTube embed ','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<iframe width="560" height="315" src="https://www.youtube.com/embed/VVEQbBvbKKQ?si=G0ogxpTr28kZ23p0" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:06:07.000000','2024-09-07 20:06:07.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(17,NULL,'Spotify embed','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'<div style="left: 0; width: 100%; height: 352px; position: relative;"><iframe src="https://open.spotify.com/embed/album/2ODvWsOgouMbaA5xf0RkJe?utm_source=oembed" style="top: 0; left: 0; width: 100%; height: 100%; position: absolute; border: 0;" allowfullscreen allow="clipboard-write; encrypted-media; fullscreen; picture-in-picture;"></iframe></div>','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:06:07.000000','2024-09-07 20:06:07.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]',NULL);
INSERT INTO contents VALUES(18,'files/GUIDELINES/HEAD_AND_NECK/Bayer-Primovist-Liver-Lesions-Poster.pdf','pdf single page','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:21:00.000000','2024-09-07 20:21:00.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','Bayer-Primovist-Liver-Lesions-Poster.pdf');
INSERT INTO contents VALUES(19,'files/GUIDELINES/HEAD_AND_NECK/2015-Clinical_value_of_relative_quantification_ultrasound_elastography_-_Fausto.pdf','pdf multiple page - USG elastography','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:21:00.000000','2024-09-07 20:21:00.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','2015-Clinical_value_of_relative_quantification_ultrasound_elastography_-_Fausto.pdf');
INSERT INTO contents VALUES(20,'files/GUIDELINES/HEAD_AND_NECK/Brain_death_diagnosis.docx','word document','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:21:00.000000','2024-09-07 20:21:00.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','Brain_death_diagnosis.docx');
INSERT INTO contents VALUES(21,'files/GUIDELINES/HEAD_AND_NECK/Clinical_Governance1.pptx','ppt files','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:35:25.000000','2024-09-07 20:35:25.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','Clinical_Governance1.pptx');
INSERT INTO contents VALUES(22,'files/GUIDELINES/HEAD_AND_NECK/Acronyms_in_MRI.xls','excel file','GUIDELINES','HEAD_AND_NECK','DRAFT',NULL,'','','English','','MEDIUM',0,0,NULL,'Title: This content belongs to GUIDELINES and the module name is HEAD_AND_NECK',1.100000000000000089,'2024-09-07 20:44:07.000000','2024-09-07 20:44:07.000000',NULL,0,0,'[{}]','Admin',NULL,0,NULL,0,'[]','{}','[]','Acronyms_in_MRI.xls');
CREATE TABLE admin_report_templates (
	id INTEGER NOT NULL, 
	template_name VARCHAR(255) NOT NULL, 
	body_part VARCHAR(13) NOT NULL, 
	modality VARCHAR(16) NOT NULL, 
	file VARCHAR(255), 
	file_path VARCHAR(255), 
	tags TEXT, 
	category VARCHAR NOT NULL, 
	module VARCHAR(16), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS "references" (
	id INTEGER NOT NULL, 
	content_id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	file_path VARCHAR(255), 
	url VARCHAR(2083), 
	embed_code TEXT, 
	description TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	category VARCHAR(22) NOT NULL, 
	module VARCHAR(16) NOT NULL, 
	file VARCHAR(255), 
	PRIMARY KEY (id), 
	CONSTRAINT fk_references_content_id FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE CASCADE ON UPDATE CASCADE, 
	FOREIGN KEY(content_id) REFERENCES contents (id)
);
CREATE TABLE IF NOT EXISTS "user_content_states" (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	content_id INTEGER, 
	modified_file_path VARCHAR(255), 
	annotations TEXT, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE, 
	FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO user_content_states VALUES(1,1,1,NULL,NULL,'2024-09-15 15:57:19.140065','2024-09-15 15:57:19.140065');
INSERT INTO user_content_states VALUES(2,2,1,NULL,NULL,'2024-09-17 00:22:08.129173','2024-09-17 00:22:08.129173');
INSERT INTO user_content_states VALUES(3,3,1,NULL,NULL,'2024-09-17 00:22:50.272035','2024-09-17 00:22:50.272035');
INSERT INTO user_content_states VALUES(4,4,1,NULL,NULL,'2024-09-19 00:58:11.043912','2024-09-19 00:58:11.043912');
CREATE TABLE IF NOT EXISTS "user_feedbacks" (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	content_id INTEGER NOT NULL, 
	feedback TEXT NOT NULL, 
	is_public BOOLEAN DEFAULT 0 NOT NULL, 
	user_display_name VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE CASCADE ON UPDATE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_profiles" (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	profile_pic VARCHAR(255), 
	profile_pic_path VARCHAR(255), 
	preferred_categories TEXT, 
	preferred_modules TEXT, 
	report_templates TEXT, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO user_profiles VALUES(1,1,'dummy_profile_pic.png','static/assets/images/dummy_profile_pic.png','guidelines,classifications,differential_diagnosis,vetting_tools,anatomy,curated_contents,report_checker,rad_calculators,tnm_staging,image_search,physics,governance_audits,courses,research_tools,music,report_template','head_and_neck,neuroradiology,chest,cardiovascular,breast,gastrointestinal,abdominal,genitourinary,musculoskeletal,vascular,pediatric,oncologic,emergency,interventional,nuclear_medicine,radiographers,others',NULL,'2024-09-15 15:57:19.140008','2024-09-15 15:57:19.140009');
INSERT INTO user_profiles VALUES(2,2,'dummy_profile_pic.png','/Users/zen/data-science/projects/ws_companion/user_data/2/profile_pic/dummy_profile_pic.png','guidelines,classifications,differential_diagnosis,vetting_tools,anatomy,curated_contents,report_checker,rad_calculators,tnm_staging,image_search,physics,governance_audits,courses,research_tools,music,report_template','head_and_neck,neuroradiology,chest,cardiovascular,breast,gastrointestinal,abdominal,genitourinary,musculoskeletal,vascular,pediatric,oncologic,emergency,interventional,nuclear_medicine,radiographers,others',NULL,'2024-09-17 00:22:08.129093','2024-09-17 00:22:08.129094');
INSERT INTO user_profiles VALUES(3,3,'IMG_6666.jpeg','/Users/zen/data-science/projects/ws_companion/user_data/3/profile_pic/IMG_6666.jpeg','guidelines,classifications,differential_diagnosis,vetting_tools,anatomy,curated_contents,report_checker,rad_calculators,tnm_staging,image_search,physics,governance_audits,courses,research_tools,music,report_template','head_and_neck,neuroradiology,chest,cardiovascular,breast,gastrointestinal,abdominal,genitourinary,musculoskeletal,vascular,pediatric,oncologic,emergency,interventional,nuclear_medicine,radiographers,others',NULL,'2024-09-17 00:22:50.271977','2024-09-17 00:23:07.516159');
INSERT INTO user_profiles VALUES(4,4,'dummy_profile_pic.png','/Users/zen/data-science/projects/ws_companion/user_data/4/profile_pic/dummy_profile_pic.png','guidelines,classifications,differential_diagnosis,vetting_tools,anatomy,curated_contents,report_checker,rad_calculators,tnm_staging,image_search,physics,governance_audits,courses,research_tools,music,report_template','head_and_neck,neuroradiology,chest,cardiovascular,breast,gastrointestinal,abdominal,genitourinary,musculoskeletal,vascular,pediatric,oncologic,emergency,interventional,nuclear_medicine,radiographers,others',NULL,'2024-09-19 00:58:11.043828','2024-09-19 00:58:11.043830');
CREATE TABLE IF NOT EXISTS "user_report_templates" (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	body_part VARCHAR NOT NULL, 
	modality VARCHAR NOT NULL, 
	template_name VARCHAR(255) NOT NULL, 
	tags TEXT, 
	is_public BOOLEAN DEFAULT 0 NOT NULL, 
	category VARCHAR, 
	module VARCHAR, 
	template_text TEXT, 
	file VARCHAR(255), 
	file_path VARCHAR(255), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_data" (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	content_id INTEGER NOT NULL, 
	interaction_type VARCHAR DEFAULT 'viewed' NOT NULL, 
	feedback TEXT, 
	content_rating INTEGER, 
	time_spent INTEGER NOT NULL, 
	last_interaction DATETIME NOT NULL, 
	last_login DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(content_id) REFERENCES contents (id) ON DELETE CASCADE ON UPDATE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO user_data VALUES(1,1,1,'loged_out',NULL,NULL,6262,'2024-09-19 00:57:35.563981','2024-09-19 00:56:46.987518');
INSERT INTO user_data VALUES(2,2,1,'loged_out',NULL,NULL,4,'2024-09-17 00:22:12.923015','2024-09-17 00:22:08.129143');
INSERT INTO user_data VALUES(3,3,1,'loged_out',NULL,NULL,23,'2024-09-17 00:23:13.394427','2024-09-17 00:22:50.272011');
INSERT INTO user_data VALUES(4,4,1,'registered',NULL,NULL,0,'2024-09-19 00:58:11.043882','2024-09-19 00:58:11.043883');
CREATE TABLE IF NOT EXISTS "users" (
	id INTEGER NOT NULL, 
	username VARCHAR(150) NOT NULL, 
	password VARCHAR(150) NOT NULL, 
	is_paid BOOLEAN, 
	is_admin BOOLEAN, 
	email VARCHAR(150) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);
INSERT INTO users VALUES(1,'admin','pbkdf2:sha256:600000$980l0bLJ0QAKRXuL$1ac86f9c87a14d5aa4285d87aa360de2644680920063bc95b07034e48058593d',0,1,'gaurav0133@gmial.com','inactive','2024-09-15 15:57:19.138248');
INSERT INTO users VALUES(2,'user2','pbkdf2:sha256:600000$cYgqmng5F7FXyL7i$9d5d41bfc735381f20143efa2cd1cf40cc046e4469db4a3feacc386bf761d5e4',0,0,'use2@gmail.com','inactive','2024-09-17 00:22:08.127170');
INSERT INTO users VALUES(3,'user4','pbkdf2:sha256:600000$zT6xDus3HQqULO2X$4da826078dc69a005053e9c8cc3e7114cbd818e0ee6e3b65c665e97d4e56bab1',0,0,'lotusheart2016@gmail.com','inactive','2024-09-17 00:22:50.270388');
INSERT INTO users VALUES(4,'user5','pbkdf2:sha256:600000$BUkR7lxXLMLHV4Zv$516fdb5d68c77e5a46e17681dd04b0d01b11f46408cee3357ada727371a2bfb0',0,0,'user5@gmail.com','active','2024-09-19 00:58:11.041099');
DELETE FROM sqlite_sequence;
CREATE INDEX ix_contents_keywords ON contents (keywords);
CREATE INDEX ix_contents_category ON contents (category);
CREATE INDEX ix_contents_id ON contents (id);
CREATE INDEX ix_contents_filepath ON contents (filepath);
CREATE INDEX ix_contents_module ON contents (module);
CREATE INDEX ix_contents_title ON contents (title);
CREATE INDEX ix_contents_content_tags ON contents (content_tags);
CREATE INDEX ix_contents_file ON contents (file);
CREATE INDEX ix_admin_report_templates_body_part ON admin_report_templates (body_part);
CREATE INDEX ix_admin_report_templates_category ON admin_report_templates (category);
CREATE INDEX ix_admin_report_templates_modality ON admin_report_templates (modality);
CREATE INDEX ix_admin_report_templates_module ON admin_report_templates (module);
CREATE UNIQUE INDEX ix_admin_report_templates_template_name ON admin_report_templates (template_name);
CREATE INDEX ix_references_category ON "references" (category);
CREATE INDEX ix_references_file ON "references" (file);
CREATE INDEX ix_references_module ON "references" (module);
CREATE UNIQUE INDEX ix_user_profiles_user_id ON user_profiles (user_id);
CREATE INDEX ix_user_report_templates_body_part ON user_report_templates (body_part);
CREATE INDEX ix_user_report_templates_category ON user_report_templates (category);
CREATE INDEX ix_user_report_templates_is_public ON user_report_templates (is_public);
CREATE INDEX ix_user_report_templates_modality ON user_report_templates (modality);
CREATE INDEX ix_user_report_templates_module ON user_report_templates (module);
CREATE UNIQUE INDEX ix_user_report_templates_template_name ON user_report_templates (template_name);
CREATE INDEX ix_user_report_templates_user_id ON user_report_templates (user_id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_users_email ON users (email);
COMMIT;
