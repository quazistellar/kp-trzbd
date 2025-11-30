from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('unireax_main', '0021_alter_practicalassignment_assignment_deadline'),
    ]

    operations = [
        # функция для проверки завершения курса
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_course_completion()
            RETURNS TRIGGER AS $$
            DECLARE
                target_user_id INTEGER;
                target_course_id BIGINT;
                course_already_completed BOOLEAN;
                all_practices_completed BOOLEAN;
                all_tests_completed BOOLEAN;
                assignment_status_name_text TEXT;
                test_passing_score INTEGER;
            BEGIN

                IF TG_TABLE_NAME = 'user_practical_assignment' THEN
                    SELECT assignment_status.assignment_status_name INTO assignment_status_name_text
                    FROM assignment_status 
                    WHERE assignment_status.id = NEW.submission_status_id;
                    
                    IF assignment_status_name_text != 'завершен' THEN
                        RETURN NEW;
                    END IF;
                    
                    SELECT user_practical_assignment.user_id, lecture.course_id INTO target_user_id, target_course_id
                    FROM user_practical_assignment
                    JOIN practical_assignment ON user_practical_assignment.practical_assignment_id = practical_assignment.id
                    JOIN lecture ON practical_assignment.lecture_id = lecture.id
                    WHERE user_practical_assignment.id = NEW.id;
                    
                ELSIF TG_TABLE_NAME = 'test_result' THEN
                    SELECT test.passing_score INTO test_passing_score
                    FROM test WHERE test.id = NEW.test_id;
                    
                    IF NOT (NEW.is_passed = TRUE OR (NEW.final_score IS NOT NULL AND NEW.final_score >= test_passing_score)) THEN
                        RETURN NEW;
                    END IF;
                    
                    SELECT test_result.user_id, lecture.course_id INTO target_user_id, target_course_id
                    FROM test_result
                    JOIN test ON test_result.test_id = test.id
                    JOIN lecture ON test.lecture_id = lecture.id
                    WHERE test_result.id = NEW.id;

                ELSIF TG_TABLE_NAME = 'feedback' THEN
                    SELECT user_practical_assignment.user_id, lecture.course_id INTO target_user_id, target_course_id
                    FROM feedback
                    JOIN user_practical_assignment ON feedback.user_practical_assignment_id = user_practical_assignment.id
                    JOIN practical_assignment ON user_practical_assignment.practical_assignment_id = practical_assignment.id
                    JOIN lecture ON practical_assignment.lecture_id = lecture.id
                    WHERE feedback.id = NEW.id;
                END IF;

                IF target_user_id IS NULL OR target_course_id IS NULL THEN
                    RETURN NEW;
                END IF;

                SELECT NOT EXISTS(
                    SELECT 1 FROM practical_assignment
                    JOIN lecture ON practical_assignment.lecture_id = lecture.id
                    LEFT JOIN user_practical_assignment ON practical_assignment.id = user_practical_assignment.practical_assignment_id 
                        AND user_practical_assignment.user_id = target_user_id
                    LEFT JOIN assignment_status ON user_practical_assignment.submission_status_id = assignment_status.id
                    WHERE lecture.course_id = target_course_id
                    AND practical_assignment.is_active = TRUE
                    AND (
                        assignment_status.assignment_status_name != 'завершен' OR 
                        assignment_status.assignment_status_name IS NULL
                    )
                ) INTO all_practices_completed;

                SELECT NOT EXISTS(
                    SELECT 1 FROM test
                    JOIN lecture ON test.lecture_id = lecture.id
                    LEFT JOIN test_result ON test.id = test_result.test_id AND test_result.user_id = target_user_id
                    WHERE lecture.course_id = target_course_id
                    AND test.is_active = TRUE
                    AND (
                        (test.grading_form = 'points' AND (test_result.final_score IS NULL OR test_result.final_score < test.passing_score)) OR
                        (test.grading_form = 'pass_fail' AND (test_result.is_passed IS NULL OR test_result.is_passed = FALSE)) OR
                        test_result.id IS NULL
                    )
                ) INTO all_tests_completed;

                SELECT status_course INTO course_already_completed
                FROM user_course 
                WHERE user_course.user_id = target_user_id AND user_course.course_id = target_course_id;
                    
                IF NOT course_already_completed AND all_practices_completed AND all_tests_completed THEN
                    CALL update_course_status(target_user_id, target_course_id);
                END IF;

                RETURN NEW;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'Ошибка при проверке завершения курса: %', SQLERRM;
                    RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS check_course_completion();"
        ),

        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS trigger_check_course_completion_practical ON user_practical_assignment;
            CREATE TRIGGER trigger_check_course_completion_practical
            AFTER INSERT OR UPDATE OF submission_status_id ON user_practical_assignment
            FOR EACH ROW
            EXECUTE FUNCTION check_course_completion();
            """,
            reverse_sql="DROP TRIGGER IF EXISTS trigger_check_course_completion_practical ON user_practical_assignment;"
        ),

        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS trigger_check_course_completion_test ON test_result;
            CREATE TRIGGER trigger_check_course_completion_test
            AFTER INSERT OR UPDATE OF is_passed, final_score ON test_result
            FOR EACH ROW
            EXECUTE FUNCTION check_course_completion();
            """,
            reverse_sql="DROP TRIGGER IF EXISTS trigger_check_course_completion_test ON test_result;"
        ),

        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS trigger_check_course_completion_feedback ON feedback;
            CREATE TRIGGER trigger_check_course_completion_feedback
            AFTER INSERT OR UPDATE OF score, is_passed ON feedback
            FOR EACH ROW
            EXECUTE FUNCTION check_course_completion();
            """,
            reverse_sql="DROP TRIGGER IF EXISTS trigger_check_course_completion_feedback ON feedback;"
        ),
    ]