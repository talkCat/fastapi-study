// Run one query block at a time in Neo4j Browser.
// All queries return graph entities so that Browser can render relationships.

// QUERY: PERSON_FULL_GRAPH
// 人员完整关系图：展示一位候选人的工作、项目、技能、专业和学习网络。
MATCH path = (person:Person {personId: 'PER001'})-[*1..4]-(related)
RETURN path
LIMIT 200;

// QUERY: PERSON_PROJECT_SKILL_POSITION_GRAPH
// 人员—项目—技能—岗位关系网络：展示项目实践所使用的技能及任职岗位。
MATCH (person:Person)-[:HAS_WORK_EXPERIENCE]->(experience:WorkExperience)
MATCH (experience)-[participation:PARTICIPATED_IN]->(project:Project)
MATCH (experience)-[positionRelation:AS_POSITION]->(position:Position)
MATCH (project)-[usage:USES_SKILL]->(skill:Skill)
RETURN person, experience, participation, project, positionRelation, position, usage, skill
LIMIT 200;

// QUERY: POSITION_CANDIDATE_EVIDENCE
// 目标岗位关联的候选人与能力证据：以 AI应用工程师为例展示岗位要求、候选人技能、项目和课程证据。
MATCH (position:Position {positionId: 'POS004'})-[requirement:REQUIRES_SKILL]->(requiredSkill:Skill)
OPTIONAL MATCH (candidate:Person)-[mastery:HAS_SKILL]->(requiredSkill)
OPTIONAL MATCH (candidate)-[:HAS_WORK_EXPERIENCE]->(experience:WorkExperience)-[participation:PARTICIPATED_IN]->(project:Project)-[usage:USES_SKILL]->(requiredSkill)
OPTIONAL MATCH (candidate)-[:HAS_LEARNING_RECORD]->(record:LearningRecord)-[learningEvidence:RELATED_TO_SKILL]->(requiredSkill)
RETURN position, requirement, requiredSkill, candidate, mastery,
       experience, participation, project, usage, record, learningEvidence
LIMIT 300;

// QUERY: COURSE_SKILL_POSITION_GRAPH
// 课程、技能与目标岗位关联图：查看课程可帮助满足哪些岗位技能要求。
MATCH (course:Course)-[coverage:COVERS_SKILL]->(skill:Skill)<-[requirement:REQUIRES_SKILL]-(position:Position)
RETURN course, coverage, skill, requirement, position
LIMIT 200;

// QUERY: SKILL_ECOSYSTEM
// 指定技能的生态关系：查看掌握、使用和学习某项技能的人员、项目和课程。
MATCH (skill:Skill {skillId: 'SK003'})
OPTIONAL MATCH (person:Person)-[mastery:HAS_SKILL]->(skill)
OPTIONAL MATCH (project:Project)-[usage:USES_SKILL]->(skill)
OPTIONAL MATCH (course:Course)-[coverage:COVERS_SKILL]->(skill)
RETURN skill, person, mastery, project, usage, course, coverage;

// QUERY: GRAPH_STATISTICS
// 快速核对导入结果中的节点数量。
MATCH (node)
RETURN labels(node) AS labels, count(*) AS count
ORDER BY labels;
