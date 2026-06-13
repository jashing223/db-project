-- 飼主表 (Owners)
CREATE TABLE Owners (
    Owner_ID INT AUTO_INCREMENT PRIMARY KEY,
    Full_Name VARCHAR(100) NOT NULL,
    Phone_Number VARCHAR(50) UNIQUE NULL,
    Email_Address VARCHAR(150) NULL,
    Physical_Address VARCHAR(255) NULL,
    Is_Anonymized BOOLEAN DEFAULT FALSE
);

-- 寵物基礎表 (PetBase)
CREATE TABLE PetBase (
    Pet_ID INT AUTO_INCREMENT PRIMARY KEY,
    Owner_ID INT NOT NULL,
    Pet_Name VARCHAR(100) NOT NULL,
    Species_Type VARCHAR(50) NOT NULL,
    Breed_Name VARCHAR(100) NULL,
    Birth_Date DATE NULL,
    Current_Weight DECIMAL(5, 2) NULL,
    FOREIGN KEY (Owner_ID) REFERENCES Owners(Owner_ID) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 員工表 (Staff)
CREATE TABLE Staff (
    Staff_ID INT AUTO_INCREMENT PRIMARY KEY,
    Staff_Name VARCHAR(100) NOT NULL,
    Role_Level INT NOT NULL,
    Status_Active BOOLEAN DEFAULT TRUE,
    Salary DECIMAL(10, 2) NULL,
    CONSTRAINT CHK_Role_Level CHECK (Role_Level BETWEEN 1 AND 4)
);

-- 醫師表 (Doctors) - 維持 Specialization 特化繼承結構
CREATE TABLE Doctors (
    Staff_ID INT PRIMARY KEY,
    License_Number VARCHAR(100) UNIQUE NOT NULL,
    Specialty VARCHAR(100) NULL,
    FOREIGN KEY (Staff_ID) REFERENCES Staff(Staff_ID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 服務目錄表 (Catalog_Items)
CREATE TABLE Catalog_Items (
    Item_ID INT AUTO_INCREMENT PRIMARY KEY,
    Item_Name VARCHAR(150) NOT NULL,
    Item_Category INT NOT NULL,
    Current_Price DECIMAL(10, 2) NOT NULL,
    Stock_Quantity INT NULL,
    Is_Discontinued BOOLEAN DEFAULT FALSE,
    CONSTRAINT CHK_Current_Price CHECK (Current_Price >= 0),
    CONSTRAINT CHK_Item_Category CHECK (Item_Category BETWEEN 1 AND 3),
    CONSTRAINT CHK_Stock_Quantity CHECK (
        (Item_Category = 1 AND Stock_Quantity >= 0) OR
        (Item_Category IN (2, 3) AND Stock_Quantity IS NULL)
    )
);

-- 預約表 (Appointments)
CREATE TABLE Appointments (
    Appointment_ID INT AUTO_INCREMENT PRIMARY KEY,
    Pet_ID INT NOT NULL,
    Doc_Staff_ID INT NOT NULL,
    Scheduled_Time DATETIME NOT NULL,
    Appt_Status INT NOT NULL,
    FOREIGN KEY (Pet_ID) REFERENCES PetBase(Pet_ID) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (Doc_Staff_ID) REFERENCES Doctors(Staff_ID) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT CHK_Appt_Status CHECK (Appt_Status BETWEEN 0 AND 2)
);

-- 病歷主檔表 (Medical_Records)
CREATE TABLE Medical_Records (
    Record_ID INT AUTO_INCREMENT PRIMARY KEY,
    Appointment_ID INT UNIQUE NOT NULL,
    Consultation_Date DATE NOT NULL,
    Clinical_Notes TEXT NULL,
    Final_Diagnosis TEXT NULL,
    Record_Locked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (Appointment_ID) REFERENCES Appointments(Appointment_ID) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 治療明細表 (Treatment_Details)
CREATE TABLE Treatment_Details (
    Detail_ID INT AUTO_INCREMENT PRIMARY KEY,
    Record_ID INT NOT NULL,
    Item_ID INT NOT NULL,
    Historical_Price DECIMAL(10, 2) NOT NULL,
    Numeric_Value DECIMAL(10, 2) NOT NULL,
    Polymorphic_Text1 VARCHAR(255) NULL,
    Polymorphic_Text2 TEXT NULL,
    FOREIGN KEY (Record_ID) REFERENCES Medical_Records(Record_ID) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (Item_ID) REFERENCES Catalog_Items(Item_ID) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT CHK_Historical_Price CHECK (Historical_Price >= 0),
    CONSTRAINT CHK_Numeric_Value CHECK (Numeric_Value > 0)
);

-- 帳單表 (Invoices)
CREATE TABLE Invoices (
    Invoice_ID INT AUTO_INCREMENT PRIMARY KEY,
    Record_ID INT UNIQUE NOT NULL,
    Total_Billed DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    Payment_Method VARCHAR(50) NULL,
    Payment_Status INT DEFAULT 0,
    FOREIGN KEY (Record_ID) REFERENCES Medical_Records(Record_ID) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT CHK_Total_Billed CHECK (Total_Billed >= 0),
    CONSTRAINT CHK_Payment_Status CHECK (Payment_Status BETWEEN 0 AND 2)
);
