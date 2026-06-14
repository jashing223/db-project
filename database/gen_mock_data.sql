-- Demo seed data from front-end/common.js getDefaultData().
-- Idempotent: safe to re-run after init.sql.
-- Appointments use CURDATE() so /appointments/today stays populated.

INSERT INTO Owners (Owner_ID, Full_Name, Phone_Number, Email_Address, Physical_Address, Is_Anonymized)
VALUES
    (1, '陳小明', '0912-345-678', NULL, NULL, FALSE),
    (2, '林美玲', '0987-654-321', NULL, NULL, FALSE),
    (3, '張大偉', '0933-111-222', NULL, NULL, FALSE)
ON DUPLICATE KEY UPDATE
    Full_Name = VALUES(Full_Name),
    Phone_Number = VALUES(Phone_Number),
    Email_Address = VALUES(Email_Address),
    Physical_Address = VALUES(Physical_Address),
    Is_Anonymized = VALUES(Is_Anonymized);

INSERT INTO PetBase (Pet_ID, Owner_ID, Pet_Name, Species_Type, Breed_Name, Birth_Date, Current_Weight)
VALUES
    (1, 1, '小白', '貓', '混種', '2024-03-10', 3.20),
    (2, 1, '旺財', '犬', '柴犬', '2022-07-22', 8.50),
    (3, 2, '毛球', '兔', NULL, '2023-11-01', 1.80),
    (4, 3, '咕嚕', '貓', '波斯', '2021-05-15', 4.10)
ON DUPLICATE KEY UPDATE
    Owner_ID = VALUES(Owner_ID),
    Pet_Name = VALUES(Pet_Name),
    Species_Type = VALUES(Species_Type),
    Breed_Name = VALUES(Breed_Name),
    Birth_Date = VALUES(Birth_Date),
    Current_Weight = VALUES(Current_Weight);

INSERT INTO Staff (Staff_ID, Staff_Name, Role_Level, Status_Active, Salary)
VALUES
    (1, '王大明', 3, TRUE, NULL),
    (2, '李小芬', 3, TRUE, NULL),
    (3, '趙志遠', 3, TRUE, NULL),
    (4, '王小美', 1, TRUE, NULL),
    (5, '陳主任', 4, TRUE, NULL),
    (6, '林護理師', 2, TRUE, NULL)
ON DUPLICATE KEY UPDATE
    Staff_Name = VALUES(Staff_Name),
    Role_Level = VALUES(Role_Level),
    Status_Active = VALUES(Status_Active);

INSERT INTO Doctors (Staff_ID, License_Number, Specialty)
VALUES
    (1, 'LIC-DEMO-001', '一般內科'),
    (2, 'LIC-DEMO-002', '外科'),
    (3, 'LIC-DEMO-003', '皮膚科')
ON DUPLICATE KEY UPDATE
    License_Number = VALUES(License_Number),
    Specialty = VALUES(Specialty);

-- Category 2/3 items must have Stock_Quantity NULL (tables.DDL CHK_Stock_Quantity).
INSERT INTO Catalog_Items (Item_ID, Item_Name, Item_Category, Current_Price, Stock_Quantity, Is_Discontinued)
VALUES
    (1, '阿莫西林 250mg', 1, 20.00, 500, FALSE),
    (2, '血液常規檢查', 2, 650.00, NULL, FALSE),
    (3, '點滴（500ml）', 3, 350.00, NULL, FALSE),
    (4, 'X 光檢查', 2, 900.00, NULL, FALSE),
    (5, '疫苗（三合一）', 1, 800.00, 30, FALSE),
    (6, '外科縫合處置', 3, 1200.00, NULL, FALSE)
ON DUPLICATE KEY UPDATE
    Item_Name = VALUES(Item_Name),
    Item_Category = VALUES(Item_Category),
    Current_Price = VALUES(Current_Price),
    Stock_Quantity = VALUES(Stock_Quantity),
    Is_Discontinued = VALUES(Is_Discontinued);

INSERT INTO Appointments (Appointment_ID, Pet_ID, Doc_Staff_ID, Scheduled_Time, Appt_Status)
VALUES
    (1, 1, 1, CONCAT(CURDATE(), ' 09:00:00'), 0),
    (2, 3, 2, CONCAT(CURDATE(), ' 10:00:00'), 0),
    (3, 4, 1, CONCAT(CURDATE(), ' 11:00:00'), 0)
ON DUPLICATE KEY UPDATE
    Pet_ID = VALUES(Pet_ID),
    Doc_Staff_ID = VALUES(Doc_Staff_ID),
    Scheduled_Time = VALUES(Scheduled_Time),
    Appt_Status = VALUES(Appt_Status);
