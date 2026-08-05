// Neo4j 5 schema for the unified talent graph POC.
// Run this script once before 02_seed_demo_data.cypher.

CREATE CONSTRAINT person_person_id_unique IF NOT EXISTS
FOR (n:Person) REQUIRE n.personId IS UNIQUE;

CREATE CONSTRAINT company_company_id_unique IF NOT EXISTS
FOR (n:Company) REQUIRE n.companyId IS UNIQUE;

CREATE CONSTRAINT industry_industry_id_unique IF NOT EXISTS
FOR (n:Industry) REQUIRE n.industryId IS UNIQUE;

CREATE CONSTRAINT region_region_id_unique IF NOT EXISTS
FOR (n:Region) REQUIRE n.regionId IS UNIQUE;

CREATE CONSTRAINT position_position_id_unique IF NOT EXISTS
FOR (n:Position) REQUIRE n.positionId IS UNIQUE;

CREATE CONSTRAINT work_experience_id_unique IF NOT EXISTS
FOR (n:WorkExperience) REQUIRE n.workExperienceId IS UNIQUE;

CREATE CONSTRAINT project_project_id_unique IF NOT EXISTS
FOR (n:Project) REQUIRE n.projectId IS UNIQUE;

CREATE CONSTRAINT skill_skill_id_unique IF NOT EXISTS
FOR (n:Skill) REQUIRE n.skillId IS UNIQUE;

CREATE CONSTRAINT major_major_id_unique IF NOT EXISTS
FOR (n:Major) REQUIRE n.majorId IS UNIQUE;

CREATE CONSTRAINT learning_record_id_unique IF NOT EXISTS
FOR (n:LearningRecord) REQUIRE n.learningRecordId IS UNIQUE;

CREATE CONSTRAINT course_course_id_unique IF NOT EXISTS
FOR (n:Course) REQUIRE n.courseId IS UNIQUE;

CREATE CONSTRAINT learning_method_id_unique IF NOT EXISTS
FOR (n:LearningMethod) REQUIRE n.methodId IS UNIQUE;

CREATE CONSTRAINT certificate_certificate_id_unique IF NOT EXISTS
FOR (n:Certificate) REQUIRE n.certificateId IS UNIQUE;

CREATE INDEX person_name_idx IF NOT EXISTS
FOR (n:Person) ON (n.name);

CREATE INDEX position_name_idx IF NOT EXISTS
FOR (n:Position) ON (n.name);

CREATE INDEX skill_name_idx IF NOT EXISTS
FOR (n:Skill) ON (n.name);

CREATE INDEX company_name_idx IF NOT EXISTS
FOR (n:Company) ON (n.name);
