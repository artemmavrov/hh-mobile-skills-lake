"""Stage 6: regional comparison of variant 9."""
from hhlake import db


def main() -> None:
    con = db.connect()
    db.open_vacancies(con)
    for script in ("target.sql", "stacks.sql", "regions.sql"):
        db.run_script(con, script)
    db.show(con, "region metrics: salaries", """
        SELECT area, it_vacancies, vacancies, share_of_it_pct, with_salary, q1, median, q3, it_median,
               premium_vs_it_pct
        FROM region_metrics""")
    db.show(con, "region metrics: vacancy profile", """
        SELECT area, avg_skills, no_skills_pct, remote_pct, senior_pct, android, ios, cross_platform
        FROM region_metrics""")
    for size, name in ((1, "skills"), (2, "pairs"), (3, "triples")):
        db.show(con, f"region top-5 {name}", f"""
            PIVOT (SELECT area, rank, stack || ' (' || vacancies || ', ' || share_pct::INT || '%)' AS cell
                   FROM region_stacks WHERE size = {size})
            ON area IN ('Москва', 'Санкт-Петербург', 'Краснодар') USING any_value(cell) GROUP BY rank ORDER BY rank""")
    db.export(con, "region_metrics", "results/analysis/region_metrics.csv")
    db.export(con, "region_stacks", "results/analysis/region_stacks.csv")
    print("saved to s3://hh-lake/results/analysis/")


if __name__ == "__main__":
    main()
