"""Stage 5: how skill pairs and triples shift the median salary of variant 9."""
from hhlake import db

EXPORTS = ("salary_overview", "salary_bands", "salary_band_skills", "pair_uplift", "triple_uplift", "skill_effect")


def main() -> None:
    con = db.connect()
    db.open_vacancies(con)
    for script in ("target.sql", "stacks.sql", "salary.sql"):
        db.run_script(con, script)
    db.show(con, "salary overview, RUB net per month", "FROM salary_overview")
    db.show(con, "salary bands: at/above vs below the median", "FROM salary_bands")
    db.show(con, "skills in high vs low salary band (>= 3 salaried vacancies)", "FROM salary_band_skills")
    db.show(con, "pairs: top 8 raising the median vs the more frequent skill",
            "FROM pair_uplift ORDER BY uplift DESC LIMIT 8")
    db.show(con, "pairs: top 8 lowering the median vs the more frequent skill",
            "FROM pair_uplift ORDER BY uplift ASC LIMIT 8")
    db.show(con, "triples: top 6 raising the median vs the most frequent pair",
            "FROM triple_uplift ORDER BY uplift DESC LIMIT 6")
    db.show(con, "triples: top 6 lowering the median vs the most frequent pair",
            "FROM triple_uplift ORDER BY uplift ASC LIMIT 6")
    db.show(con, "summary: effect of the added skill", "FROM skill_effect")
    for table in EXPORTS:
        db.export(con, table, f"results/analysis/{table}.csv")
    print("saved to s3://hh-lake/results/analysis/")


if __name__ == "__main__":
    main()
