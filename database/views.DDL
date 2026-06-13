-- 寵物 (Pets) - 操作 interface
CREATE OR REPLACE VIEW Pets AS
SELECT
    Pet_ID,
    Owner_ID,
    Pet_Name,
    Species_Type,
    Breed_Name,
    Birth_Date,
    Current_Weight,
    CASE
        WHEN Birth_Date IS NOT NULL THEN TIMESTAMPDIFF(YEAR, Birth_Date, CURDATE())
        ELSE 0
    END AS Age
FROM PetBase;
