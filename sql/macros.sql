-- Monthly net salary in rubles: middle of the range, gross converted at 13% income tax,
-- foreign currencies at fixed mid-2024 rates; other currencies are left out.
CREATE OR REPLACE MACRO net_salary_rub(s) AS
    coalesce(
        (TRY_CAST(s."from" AS DOUBLE) + TRY_CAST(s."to" AS DOUBLE)) / 2,
        TRY_CAST(s."from" AS DOUBLE),
        TRY_CAST(s."to" AS DOUBLE)
    )
    * CASE s.currency WHEN 'RUR' THEN 1 WHEN 'USD' THEN 90 WHEN 'EUR' THEN 98 END
    * CASE WHEN s.gross = 'true' THEN 0.87 ELSE 1 END;
