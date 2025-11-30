from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('unireax_main', '0024_alter_viewassignmentsubmissions_options_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION calculate_course_completion(p_user_id INTEGER, p_course_id BIGINT)
            RETURNS DECIMAL(5,2) AS $$
            DECLARE
                total_practices INTEGER;
                completed_practices INTEGER;
                total_tests INTEGER;
                completed_tests INTEGER;
                total_items INTEGER;
                completed_items INTEGER;
                completion_percent DECIMAL(5,2);
            BEGIN
                SELECT COUNT(*) INTO total_practices
                FROM practical_assignment
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id 
                AND practical_assignment.is_active = TRUE;

                SELECT COUNT(*) INTO completed_practices
                FROM user_practical_assignment upa
                JOIN practical_assignment pa ON upa.practical_assignment_id = pa.id
                JOIN lecture ON pa.lecture_id = lecture.id
                JOIN assignment_status ast ON upa.submission_status_id = ast.id
                WHERE lecture.course_id = p_course_id
                AND upa.user_id = p_user_id
                AND ast.assignment_status_name = 'завершен';

                SELECT COUNT(*) INTO total_tests
                FROM test
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id 
                AND test.is_active = TRUE;

                SELECT COUNT(DISTINCT test.id) INTO completed_tests  
                FROM test_result tr
                JOIN test ON tr.test_id = test.id
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id
                AND tr.user_id = p_user_id
                AND (
                    (test.grading_form = 'points' AND tr.final_score >= test.passing_score)
                    OR 
                    (test.grading_form = 'pass_fail' AND tr.is_passed = TRUE)
                );

                total_items := total_practices + total_tests;
                completed_items := completed_practices + completed_tests;

                IF total_items = 0 THEN
                    RETURN 0.00;
                END IF;

                completion_percent := (completed_items::DECIMAL / total_items * 100)::DECIMAL(5,2);
                
                IF completion_percent > 100 THEN
                    RETURN 100.00;
                END IF;
                
                RETURN completion_percent;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RETURN 0.00;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS calculate_course_completion(INTEGER, BIGINT);"
        ),
    ]