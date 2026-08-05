// Neo4j 5 native Cypher seed data.
// All names and organizations in this file are fictional.
// This script is idempotent: it uses MERGE for every node and relationship.

// 1. Shared reference entities
UNWIND [
  {industryId: 'IND001', name: '软件和信息技术服务业'},
  {industryId: 'IND002', name: '智能制造'},
  {industryId: 'IND003', name: '工业互联网'}
] AS row
MERGE (industry:Industry {industryId: row.industryId})
SET industry += row;

UNWIND [
  {regionId: 'REG001', name: '武汉市', level: 'city'},
  {regionId: 'REG002', name: '东湖高新区', level: 'district'},
  {regionId: 'REG003', name: '武汉经济技术开发区', level: 'district'}
] AS row
MERGE (region:Region {regionId: row.regionId})
SET region += row;

UNWIND [
  {companyId: 'COM001', name: '江城数智科技有限公司', scale: '100-499人'},
  {companyId: 'COM002', name: '光谷智联软件有限公司', scale: '500-999人'},
  {companyId: 'COM003', name: '长江智造有限公司', scale: '1000人以上'},
  {companyId: 'COM004', name: '华中云服科技有限公司', scale: '100-499人'}
] AS row
MERGE (company:Company {companyId: row.companyId})
SET company += row;

UNWIND [
  {positionId: 'POS001', name: 'Java后端工程师', category: '研发'},
  {positionId: 'POS002', name: '数据分析师', category: '数据'},
  {positionId: 'POS003', name: '前端工程师', category: '研发'},
  {positionId: 'POS004', name: 'AI应用工程师', category: '人工智能'},
  {positionId: 'POS005', name: '数据工程师', category: '数据'}
] AS row
MERGE (position:Position {positionId: row.positionId})
SET position += row;

UNWIND [
  {skillId: 'SK001', name: 'Java', category: '编程语言'},
  {skillId: 'SK002', name: 'Spring Boot', category: '后端框架'},
  {skillId: 'SK003', name: 'Neo4j', category: '图数据库'},
  {skillId: 'SK004', name: 'Python', category: '编程语言'},
  {skillId: 'SK005', name: 'SQL', category: '数据技术'},
  {skillId: 'SK006', name: 'Vue.js', category: '前端框架'},
  {skillId: 'SK007', name: 'Docker', category: '工程化'},
  {skillId: 'SK008', name: '数据建模', category: '数据技术'},
  {skillId: 'SK009', name: 'RAG', category: '人工智能'},
  {skillId: 'SK010', name: '机器学习', category: '人工智能'},
  {skillId: 'SK011', name: 'JavaScript', category: '编程语言'}
] AS row
MERGE (skill:Skill {skillId: row.skillId})
SET skill += row;

UNWIND [
  {majorId: 'MAJ001', name: '计算机科学与技术'},
  {majorId: 'MAJ002', name: '信息管理与信息系统'},
  {majorId: 'MAJ003', name: '软件工程'},
  {majorId: 'MAJ004', name: '数据科学与大数据技术'}
] AS row
MERGE (major:Major {majorId: row.majorId})
SET major += row;

UNWIND [
  {methodId: 'MET001', name: '线上自学'},
  {methodId: 'MET002', name: '集中培训'},
  {methodId: 'MET003', name: '项目实践'}
] AS row
MERGE (method:LearningMethod {methodId: row.methodId})
SET method += row;

UNWIND [
  {courseId: 'COU001', name: '图数据库与Neo4j实践', provider: '虚构技术学院'},
  {courseId: 'COU002', name: 'Spring Boot微服务实战', provider: '虚构技术学院'},
  {courseId: 'COU003', name: 'Python数据分析基础', provider: '虚构数据学院'},
  {courseId: 'COU004', name: 'Vue 3企业级开发', provider: '虚构技术学院'},
  {courseId: 'COU005', name: '检索增强生成应用开发', provider: '虚构AI学院'},
  {courseId: 'COU006', name: '数据仓库与维度建模', provider: '虚构数据学院'}
] AS row
MERGE (course:Course {courseId: row.courseId})
SET course += row;

UNWIND [
  {certificateId: 'CER001', name: 'Neo4j图数据基础认证', issuer: '虚构认证机构'},
  {certificateId: 'CER002', name: '数据分析能力认证', issuer: '虚构认证机构'},
  {certificateId: 'CER003', name: '云原生基础认证', issuer: '虚构认证机构'}
] AS row
MERGE (certificate:Certificate {certificateId: row.certificateId})
SET certificate += row;

// 2. Candidate profiles, work history, projects, and learning records
UNWIND [
  {personId: 'PER001', name: '林澈', city: '武汉市', yearsOfExperience: 5, summary: '后端与图数据方向研发人员'},
  {personId: 'PER002', name: '周宁', city: '武汉市', yearsOfExperience: 4, summary: '数据分析与数据工程方向人员'},
  {personId: 'PER003', name: '陈曦', city: '武汉市', yearsOfExperience: 3, summary: '前端与交互开发方向人员'},
  {personId: 'PER004', name: '孙越', city: '武汉市', yearsOfExperience: 6, summary: 'AI应用与智能制造数字化方向人员'}
] AS row
MERGE (person:Person {personId: row.personId})
SET person += row;

UNWIND [
  {workExperienceId: 'WE001', startDate: date('2021-07-01'), endDate: date('2023-10-31'), isCurrent: false, description: '负责招聘平台后端服务与接口建设'},
  {workExperienceId: 'WE002', startDate: date('2023-11-01'), endDate: null, isCurrent: true, description: '负责AI应用与人才图谱服务研发'},
  {workExperienceId: 'WE003', startDate: date('2020-07-01'), endDate: date('2022-12-31'), isCurrent: false, description: '负责运营分析报表和指标体系建设'},
  {workExperienceId: 'WE004', startDate: date('2023-01-01'), endDate: null, isCurrent: true, description: '负责制造数据治理和数据管道建设'},
  {workExperienceId: 'WE005', startDate: date('2022-07-01'), endDate: null, isCurrent: true, description: '负责招聘系统前端和可视化页面开发'},
  {workExperienceId: 'WE006', startDate: date('2019-07-01'), endDate: null, isCurrent: true, description: '负责工业知识助手与智能质检应用研发'}
] AS row
MERGE (experience:WorkExperience {workExperienceId: row.workExperienceId})
SET experience += row;

UNWIND [
  {projectId: 'PRJ001', name: '招聘智能助手', startDate: date('2022-03-01'), endDate: date('2023-08-31'), description: '面向招聘业务的智能问答与办理入口推荐'},
  {projectId: 'PRJ002', name: '人才统一图谱', startDate: date('2024-01-01'), endDate: null, description: '融合简历和学习信息的人才关系网络'},
  {projectId: 'PRJ003', name: '运营数据看板', startDate: date('2021-01-01'), endDate: date('2022-11-30'), description: '运营指标分析与自助取数'},
  {projectId: 'PRJ004', name: '制造数据中台', startDate: date('2023-04-01'), endDate: null, description: '生产与质量数据标准化汇聚'},
  {projectId: 'PRJ005', name: '招聘管理前端重构', startDate: date('2023-02-01'), endDate: null, description: '招聘业务页面与数据可视化重构'},
  {projectId: 'PRJ006', name: '工业知识助手', startDate: date('2023-06-01'), endDate: null, description: '面向设备运维场景的RAG应用'}
] AS row
MERGE (project:Project {projectId: row.projectId})
SET project += row;

UNWIND [
  {learningRecordId: 'LR001', startDate: date('2023-09-01'), endDate: date('2023-10-15'), status: '已完成', score: 92},
  {learningRecordId: 'LR002', startDate: date('2022-01-10'), endDate: date('2022-03-20'), status: '已完成', score: 88},
  {learningRecordId: 'LR003', startDate: date('2022-10-01'), endDate: date('2022-12-20'), status: '已完成', score: 90},
  {learningRecordId: 'LR004', startDate: date('2024-02-01'), endDate: date('2024-04-30'), status: '已完成', score: 94},
  {learningRecordId: 'LR005', startDate: date('2023-01-01'), endDate: date('2023-02-28'), status: '已完成', score: 91},
  {learningRecordId: 'LR006', startDate: date('2024-03-01'), endDate: null, status: '学习中', score: null},
  {learningRecordId: 'LR007', startDate: date('2023-09-01'), endDate: date('2023-11-30'), status: '已完成', score: 89},
  {learningRecordId: 'LR008', startDate: date('2024-01-15'), endDate: date('2024-03-15'), status: '已完成', score: 95}
] AS row
MERGE (record:LearningRecord {learningRecordId: row.learningRecordId})
SET record += row;

// 3. Shared reference relationships
UNWIND [
  {companyId: 'COM001', industryId: 'IND001'}, {companyId: 'COM002', industryId: 'IND001'},
  {companyId: 'COM003', industryId: 'IND002'}, {companyId: 'COM004', industryId: 'IND003'}
] AS row
MATCH (company:Company {companyId: row.companyId})
MATCH (industry:Industry {industryId: row.industryId})
MERGE (company)-[:IN_INDUSTRY]->(industry);

UNWIND [
  {companyId: 'COM001', regionId: 'REG002'}, {companyId: 'COM002', regionId: 'REG002'},
  {companyId: 'COM003', regionId: 'REG003'}, {companyId: 'COM004', regionId: 'REG001'}
] AS row
MATCH (company:Company {companyId: row.companyId})
MATCH (region:Region {regionId: row.regionId})
MERGE (company)-[:LOCATED_IN]->(region);

UNWIND [
  {courseId: 'COU001', skillId: 'SK003', coverageLevel: 3},
  {courseId: 'COU002', skillId: 'SK002', coverageLevel: 4},
  {courseId: 'COU002', skillId: 'SK007', coverageLevel: 2},
  {courseId: 'COU003', skillId: 'SK004', coverageLevel: 3},
  {courseId: 'COU003', skillId: 'SK005', coverageLevel: 3},
  {courseId: 'COU004', skillId: 'SK006', coverageLevel: 4},
  {courseId: 'COU004', skillId: 'SK011', coverageLevel: 3},
  {courseId: 'COU005', skillId: 'SK009', coverageLevel: 4},
  {courseId: 'COU005', skillId: 'SK010', coverageLevel: 3},
  {courseId: 'COU006', skillId: 'SK005', coverageLevel: 4},
  {courseId: 'COU006', skillId: 'SK008', coverageLevel: 4}
] AS row
MATCH (course:Course {courseId: row.courseId})
MATCH (skill:Skill {skillId: row.skillId})
MERGE (course)-[coverage:COVERS_SKILL]->(skill)
SET coverage.coverageLevel = row.coverageLevel;

UNWIND [
  {positionId: 'POS001', skillId: 'SK001', minimumLevel: 4}, {positionId: 'POS001', skillId: 'SK002', minimumLevel: 3},
  {positionId: 'POS001', skillId: 'SK003', minimumLevel: 2}, {positionId: 'POS001', skillId: 'SK007', minimumLevel: 2},
  {positionId: 'POS002', skillId: 'SK004', minimumLevel: 3}, {positionId: 'POS002', skillId: 'SK005', minimumLevel: 4},
  {positionId: 'POS002', skillId: 'SK008', minimumLevel: 3}, {positionId: 'POS003', skillId: 'SK006', minimumLevel: 4},
  {positionId: 'POS003', skillId: 'SK011', minimumLevel: 4}, {positionId: 'POS003', skillId: 'SK007', minimumLevel: 2},
  {positionId: 'POS004', skillId: 'SK004', minimumLevel: 3}, {positionId: 'POS004', skillId: 'SK009', minimumLevel: 3},
  {positionId: 'POS004', skillId: 'SK010', minimumLevel: 3}, {positionId: 'POS004', skillId: 'SK003', minimumLevel: 2},
  {positionId: 'POS005', skillId: 'SK004', minimumLevel: 4}, {positionId: 'POS005', skillId: 'SK005', minimumLevel: 4},
  {positionId: 'POS005', skillId: 'SK008', minimumLevel: 4}, {positionId: 'POS005', skillId: 'SK007', minimumLevel: 3}
] AS row
MATCH (position:Position {positionId: row.positionId})
MATCH (skill:Skill {skillId: row.skillId})
MERGE (position)-[requirement:REQUIRES_SKILL]->(skill)
SET requirement.minimumLevel = row.minimumLevel;

UNWIND [
  {projectId: 'PRJ001', skillId: 'SK001'}, {projectId: 'PRJ001', skillId: 'SK002'},
  {projectId: 'PRJ001', skillId: 'SK007'}, {projectId: 'PRJ002', skillId: 'SK003'},
  {projectId: 'PRJ002', skillId: 'SK001'}, {projectId: 'PRJ002', skillId: 'SK009'},
  {projectId: 'PRJ003', skillId: 'SK004'}, {projectId: 'PRJ003', skillId: 'SK005'},
  {projectId: 'PRJ003', skillId: 'SK008'}, {projectId: 'PRJ004', skillId: 'SK004'},
  {projectId: 'PRJ004', skillId: 'SK005'}, {projectId: 'PRJ004', skillId: 'SK008'},
  {projectId: 'PRJ004', skillId: 'SK007'}, {projectId: 'PRJ005', skillId: 'SK006'},
  {projectId: 'PRJ005', skillId: 'SK011'}, {projectId: 'PRJ006', skillId: 'SK004'},
  {projectId: 'PRJ006', skillId: 'SK009'}, {projectId: 'PRJ006', skillId: 'SK010'}
] AS row
MATCH (project:Project {projectId: row.projectId})
MATCH (skill:Skill {skillId: row.skillId})
MERGE (project)-[:USES_SKILL]->(skill);

// 4. Person-specific work and learning facts
UNWIND [
  {personId: 'PER001', majorId: 'MAJ001'}, {personId: 'PER002', majorId: 'MAJ002'},
  {personId: 'PER003', majorId: 'MAJ003'}, {personId: 'PER004', majorId: 'MAJ004'}
] AS row
MATCH (person:Person {personId: row.personId})
MATCH (major:Major {majorId: row.majorId})
MERGE (person)-[:MAJORED_IN]->(major);

UNWIND [
  {personId: 'PER001', positionId: 'POS004'}, {personId: 'PER002', positionId: 'POS005'},
  {personId: 'PER003', positionId: 'POS003'}, {personId: 'PER004', positionId: 'POS004'}
] AS row
MATCH (person:Person {personId: row.personId})
MATCH (position:Position {positionId: row.positionId})
MERGE (person)-[:TARGETS]->(position);

UNWIND [
  {personId: 'PER001', workExperienceId: 'WE001'}, {personId: 'PER001', workExperienceId: 'WE002'},
  {personId: 'PER002', workExperienceId: 'WE003'}, {personId: 'PER002', workExperienceId: 'WE004'},
  {personId: 'PER003', workExperienceId: 'WE005'}, {personId: 'PER004', workExperienceId: 'WE006'}
] AS row
MATCH (person:Person {personId: row.personId})
MATCH (experience:WorkExperience {workExperienceId: row.workExperienceId})
MERGE (person)-[:HAS_WORK_EXPERIENCE]->(experience);

UNWIND [
  {workExperienceId: 'WE001', companyId: 'COM001', positionId: 'POS001'},
  {workExperienceId: 'WE002', companyId: 'COM004', positionId: 'POS004'},
  {workExperienceId: 'WE003', companyId: 'COM002', positionId: 'POS002'},
  {workExperienceId: 'WE004', companyId: 'COM003', positionId: 'POS005'},
  {workExperienceId: 'WE005', companyId: 'COM002', positionId: 'POS003'},
  {workExperienceId: 'WE006', companyId: 'COM003', positionId: 'POS004'}
] AS row
MATCH (experience:WorkExperience {workExperienceId: row.workExperienceId})
MATCH (company:Company {companyId: row.companyId})
MATCH (position:Position {positionId: row.positionId})
MERGE (experience)-[:AT_COMPANY]->(company)
MERGE (experience)-[:AS_POSITION]->(position);

UNWIND [
  {workExperienceId: 'WE001', projectId: 'PRJ001', role: '后端负责人'},
  {workExperienceId: 'WE002', projectId: 'PRJ002', role: '图谱服务研发'},
  {workExperienceId: 'WE003', projectId: 'PRJ003', role: '数据分析师'},
  {workExperienceId: 'WE004', projectId: 'PRJ004', role: '数据工程师'},
  {workExperienceId: 'WE005', projectId: 'PRJ005', role: '前端工程师'},
  {workExperienceId: 'WE006', projectId: 'PRJ006', role: 'AI应用工程师'}
] AS row
MATCH (experience:WorkExperience {workExperienceId: row.workExperienceId})
MATCH (project:Project {projectId: row.projectId})
MERGE (experience)-[participation:PARTICIPATED_IN]->(project)
SET participation.role = row.role;

UNWIND [
  {personId: 'PER001', skillId: 'SK001', proficiencyLevel: 4, acquiredDate: date('2021-07-01'), source: '工作经历'},
  {personId: 'PER001', skillId: 'SK002', proficiencyLevel: 4, acquiredDate: date('2021-07-01'), source: '项目实践'},
  {personId: 'PER001', skillId: 'SK003', proficiencyLevel: 3, acquiredDate: date('2023-10-15'), source: '课程学习'},
  {personId: 'PER001', skillId: 'SK007', proficiencyLevel: 3, acquiredDate: date('2022-03-01'), source: '项目实践'},
  {personId: 'PER001', skillId: 'SK009', proficiencyLevel: 2, acquiredDate: date('2024-01-01'), source: '项目实践'},
  {personId: 'PER002', skillId: 'SK004', proficiencyLevel: 4, acquiredDate: date('2020-07-01'), source: '工作经历'},
  {personId: 'PER002', skillId: 'SK005', proficiencyLevel: 4, acquiredDate: date('2020-07-01'), source: '工作经历'},
  {personId: 'PER002', skillId: 'SK008', proficiencyLevel: 4, acquiredDate: date('2023-01-01'), source: '项目实践'},
  {personId: 'PER002', skillId: 'SK007', proficiencyLevel: 3, acquiredDate: date('2023-01-01'), source: '项目实践'},
  {personId: 'PER003', skillId: 'SK006', proficiencyLevel: 4, acquiredDate: date('2022-07-01'), source: '工作经历'},
  {personId: 'PER003', skillId: 'SK011', proficiencyLevel: 4, acquiredDate: date('2022-07-01'), source: '工作经历'},
  {personId: 'PER003', skillId: 'SK007', proficiencyLevel: 2, acquiredDate: date('2024-03-01'), source: '课程学习'},
  {personId: 'PER004', skillId: 'SK004', proficiencyLevel: 4, acquiredDate: date('2019-07-01'), source: '工作经历'},
  {personId: 'PER004', skillId: 'SK009', proficiencyLevel: 4, acquiredDate: date('2023-06-01'), source: '项目实践'},
  {personId: 'PER004', skillId: 'SK010', proficiencyLevel: 3, acquiredDate: date('2023-06-01'), source: '课程学习'},
  {personId: 'PER004', skillId: 'SK003', proficiencyLevel: 2, acquiredDate: date('2023-09-01'), source: '课程学习'}
] AS row
MATCH (person:Person {personId: row.personId})
MATCH (skill:Skill {skillId: row.skillId})
MERGE (person)-[mastery:HAS_SKILL]->(skill)
SET mastery.proficiencyLevel = row.proficiencyLevel,
    mastery.acquiredDate = row.acquiredDate,
    mastery.source = row.source;

UNWIND [
  {personId: 'PER001', learningRecordId: 'LR001', courseId: 'COU001', methodId: 'MET002'},
  {personId: 'PER001', learningRecordId: 'LR002', courseId: 'COU002', methodId: 'MET001'},
  {personId: 'PER002', learningRecordId: 'LR003', courseId: 'COU003', methodId: 'MET001'},
  {personId: 'PER002', learningRecordId: 'LR004', courseId: 'COU006', methodId: 'MET003'},
  {personId: 'PER003', learningRecordId: 'LR005', courseId: 'COU004', methodId: 'MET002'},
  {personId: 'PER003', learningRecordId: 'LR006', courseId: 'COU002', methodId: 'MET001'},
  {personId: 'PER004', learningRecordId: 'LR007', courseId: 'COU005', methodId: 'MET002'},
  {personId: 'PER004', learningRecordId: 'LR008', courseId: 'COU001', methodId: 'MET001'}
] AS row
MATCH (person:Person {personId: row.personId})
MATCH (record:LearningRecord {learningRecordId: row.learningRecordId})
MATCH (course:Course {courseId: row.courseId})
MATCH (method:LearningMethod {methodId: row.methodId})
MERGE (person)-[:HAS_LEARNING_RECORD]->(record)
MERGE (record)-[:LEARNED_COURSE]->(course)
MERGE (record)-[:LEARNED_BY]->(method);

UNWIND [
  {learningRecordId: 'LR001', skillId: 'SK003'}, {learningRecordId: 'LR002', skillId: 'SK002'},
  {learningRecordId: 'LR003', skillId: 'SK004'}, {learningRecordId: 'LR003', skillId: 'SK005'},
  {learningRecordId: 'LR004', skillId: 'SK005'}, {learningRecordId: 'LR004', skillId: 'SK008'},
  {learningRecordId: 'LR005', skillId: 'SK006'}, {learningRecordId: 'LR005', skillId: 'SK011'},
  {learningRecordId: 'LR006', skillId: 'SK002'}, {learningRecordId: 'LR007', skillId: 'SK009'},
  {learningRecordId: 'LR007', skillId: 'SK010'}, {learningRecordId: 'LR008', skillId: 'SK003'}
] AS row
MATCH (record:LearningRecord {learningRecordId: row.learningRecordId})
MATCH (skill:Skill {skillId: row.skillId})
MERGE (record)-[:RELATED_TO_SKILL]->(skill);

UNWIND [
  {learningRecordId: 'LR001', certificateId: 'CER001'},
  {learningRecordId: 'LR003', certificateId: 'CER002'},
  {learningRecordId: 'LR004', certificateId: 'CER003'}
] AS row
MATCH (record:LearningRecord {learningRecordId: row.learningRecordId})
MATCH (certificate:Certificate {certificateId: row.certificateId})
MERGE (record)-[:EARNED]->(certificate);
