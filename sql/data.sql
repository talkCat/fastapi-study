USE fastapi_study;

-- 插入用户数据（密码都是明文 "password123"）
INSERT INTO users (username, email, hashed_password, full_name, role, is_active) VALUES
('admin', 'admin@example.com', 'password123', '系统管理员', 'admin', TRUE),
('john', 'john@example.com', 'password123', 'John Doe', 'user', TRUE),
('jane', 'jane@example.com', 'password123', 'Jane Smith', 'user', TRUE),
('bob', 'bob@example.com', 'password123', 'Bob Wilson', 'guest', TRUE),
('alice', 'alice@example.com', 'password123', 'Alice Brown', 'user', TRUE);

-- 插入物品数据
INSERT INTO items (name, description, price, category, owner_id) VALUES
('iPhone 15 Pro', '苹果最新款智能手机，256GB深空黑', 8999.00, 'electronics', 2),
('MacBook Pro 14', 'M3 Pro芯片，18GB内存，512GB SSD', 14999.00, 'electronics', 2),
('AirPods Pro 2', '主动降噪无线耳机', 1899.00, 'electronics', 3),
('iPad Air', '10.9英寸M1芯片平板电脑', 4799.00, 'electronics', 3),
('Python Cookbook', 'Python编程进阶指南，第三版', 89.00, 'books', 4),
('Clean Code', '代码整洁之道，Robert C. Martin著', 59.00, 'books', 4),
('Design Patterns', '设计模式：可复用面向对象软件的基础', 79.00, 'books', 5),
('The Pragmatic Programmer', '程序员修炼之道', 69.00, 'books', 5),
('Nike Air Max', '男子运动鞋，黑色经典款', 899.00, 'clothing', 2),
('Adidas Ultraboost', '跑步鞋，舒适缓震', 1299.00, 'clothing', 3),
('Levis 501', '经典直筒牛仔裤', 599.00, 'clothing', 4),
('Uniqlo HEATTECH', '发热内衣套装', 199.00, 'clothing', 5),
('Sony WH-1000XM5', '索尼顶级降噪耳机', 2499.00, 'electronics', 2),
('Samsung Galaxy S24', '三星旗舰手机', 6999.00, 'electronics', 3),
('The Great Gatsby', '了不起的盖茨比，英文原版', 45.00, 'books', 4);