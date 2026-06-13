DELIMITER $$

-- =========================================================================
-- Trigger 1: 寫入明細前 (防禦鎖定竄改 & 強制覆寫歷史單價)
-- =========================================================================

CREATE TRIGGER trg_td_before_insert
BEFORE INSERT ON Treatment_Details
FOR EACH ROW
BEGIN
    DECLARE v_is_locked BOOLEAN;
    DECLARE v_current_price DECIMAL(10,2);

    -- 1. 檢查病歷鎖定狀態 (防護機制)
    SELECT Record_Locked INTO v_is_locked 
    FROM Medical_Records 
    WHERE Record_ID = NEW.Record_ID;

    -- 若病歷已鎖定，立刻拋出錯誤並終止 INSERT 操作
    IF v_is_locked = TRUE THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Transaction Rejected: Medical Record is locked.';
    END IF;

    -- 2. 若病歷未鎖定，則無視前端傳入的 Historical_Price，強制從 Catalog 撈取當下價格覆寫
    SELECT Current_Price INTO v_current_price 
    FROM Catalog_Items 
    WHERE Item_ID = NEW.Item_ID;
    
    SET NEW.Historical_Price = v_current_price;
END$$

-- =========================================================================
-- Trigger 2: 更新明細前 (防禦鎖定竄改 & 變更項目時重抓單價)
-- =========================================================================
CREATE TRIGGER trg_td_before_update
BEFORE UPDATE ON Treatment_Details
FOR EACH ROW
BEGIN
    DECLARE v_is_locked BOOLEAN;
    DECLARE v_current_price DECIMAL(10,2);
    
    -- 檢查病歷鎖定狀態
    SELECT Record_Locked INTO v_is_locked FROM Medical_Records WHERE Record_ID = NEW.Record_ID;
    IF v_is_locked = TRUE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Transaction Rejected: Medical Record is locked.';
    END IF;
    
    -- 若中介層變更了服務項目，強制重抓價格
    IF NEW.Item_ID != OLD.Item_ID THEN
        SELECT Current_Price INTO v_current_price FROM Catalog_Items WHERE Item_ID = NEW.Item_ID;
        SET NEW.Historical_Price = v_current_price;
    END IF;
END$$

-- =========================================================================
-- Trigger 3: 刪除明細前 (防禦鎖定竄改)
-- =========================================================================
CREATE TRIGGER trg_td_before_delete
BEFORE DELETE ON Treatment_Details
FOR EACH ROW
BEGIN
    DECLARE v_is_locked BOOLEAN;
    SELECT Record_Locked INTO v_is_locked FROM Medical_Records WHERE Record_ID = OLD.Record_ID;
    IF v_is_locked = TRUE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Transaction Rejected: Cannot delete details from a locked medical record.';
    END IF;
END$$

-- =========================================================================
-- Trigger 4-1: 新增明細後 (帳單總額聯動結算)
-- =========================================================================
CREATE TRIGGER trg_td_after_insert
AFTER INSERT ON Treatment_Details
FOR EACH ROW
BEGIN
    UPDATE Invoices 
    SET Total_Billed = COALESCE(Total_Billed, 0) + (NEW.Historical_Price * NEW.Numeric_Value)
    WHERE Record_ID = NEW.Record_ID;
END$$

-- =========================================================================
-- Trigger 4-2: 更新明細後 (帳單總額聯動結算)
-- =========================================================================
CREATE TRIGGER trg_td_after_update
AFTER UPDATE ON Treatment_Details
FOR EACH ROW
BEGIN
    UPDATE Invoices 
    SET Total_Billed = COALESCE(Total_Billed, 0) - (OLD.Historical_Price * OLD.Numeric_Value) + (NEW.Historical_Price * NEW.Numeric_Value)
    WHERE Record_ID = NEW.Record_ID;
END$$

-- =========================================================================
-- Trigger 4-3: 刪除明細後 (帳單總額聯動結算)
-- =========================================================================
CREATE TRIGGER trg_td_after_delete
AFTER DELETE ON Treatment_Details
FOR EACH ROW
BEGIN
    UPDATE Invoices 
    SET Total_Billed = COALESCE(Total_Billed, 0) - (OLD.Historical_Price * OLD.Numeric_Value)
    WHERE Record_ID = OLD.Record_ID;
END$$

-- =========================================================================
-- Trigger 5: 狀態鎖定觸發庫存實體扣減
-- =========================================================================
CREATE TRIGGER trg_mr_after_update
AFTER UPDATE ON Medical_Records
FOR EACH ROW
BEGIN
    -- 當狀態嚴格從 0 (False) 轉為 1 (True) 時觸發
    IF NEW.Record_Locked = TRUE AND OLD.Record_Locked = FALSE THEN
        -- 將該病歷下所有 Item_Category = 1 (藥品) 的數量，從 Catalog_Items 中扣除
        UPDATE Catalog_Items c
        JOIN Treatment_Details t ON c.Item_ID = t.Item_ID
        SET c.Stock_Quantity = c.Stock_Quantity - t.Numeric_Value
        WHERE t.Record_ID = NEW.Record_ID
          AND c.Item_Category = 1;
    END IF;
END$$

DELIMITER ;
