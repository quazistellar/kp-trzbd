from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('unireax_main', '0018_viewassignmentsubmissions_and_more'),
    ]

    operations = [
        # 1. функция: средний рейтинг курса
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION calculate_course_rating(p_course_id BIGINT)
            RETURNS DECIMAL(3,2) AS $$
            DECLARE
                avg_rating DECIMAL(3,2);
            BEGIN
                SELECT AVG(review.rating)::DECIMAL(3,2) INTO avg_rating
                FROM review
                WHERE review.course_id = p_course_id;
                
                RETURN COALESCE(avg_rating, 0.00);
            EXCEPTION
                WHEN OTHERS THEN
                    RETURN 0.00;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS calculate_course_rating(BIGINT);"
        ),

        # 2. функция: процент завершенности курса (
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION calculate_course_completion(p_user_id INTEGER, p_course_id BIGINT)
            RETURNS DECIMAL(5,2) AS $$
            DECLARE
                total_lectures INTEGER;
                total_practices INTEGER;
                completed_practices INTEGER;
                total_tests INTEGER;
                completed_tests INTEGER;
                total_items INTEGER;
                completed_items INTEGER;
                completion_percent DECIMAL(5,2);
            BEGIN
                SELECT COUNT(*) INTO total_lectures
                FROM lecture
                WHERE lecture.course_id = p_course_id 
                AND lecture.is_active = TRUE;

                SELECT COUNT(*) INTO total_practices
                FROM practical_assignment
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id 
                AND practical_assignment.is_active = TRUE;


                SELECT COUNT(*) INTO completed_practices
                FROM user_practical_assignment
                JOIN practical_assignment ON user_practical_assignment.practical_assignment_id = practical_assignment.id
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                JOIN assignment_status ON user_practical_assignment.submission_status_id = assignment_status.id
                WHERE lecture.course_id = p_course_id
                AND user_practical_assignment.user_id = p_user_id
                AND assignment_status.assignment_status_name = 'завершен';


                SELECT COUNT(*) INTO total_tests
                FROM test
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id 
                AND test.is_active = TRUE;

                SELECT COUNT(DISTINCT test.id) INTO completed_tests  
                FROM test_result
                JOIN test ON test_result.test_id = test.id
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id
                AND test_result.user_id = p_user_id
                AND (
                    (test.grading_form = 'points' AND test_result.final_score >= test.passing_score)
                    OR (test.grading_form = 'pass_fail' AND test_result.is_passed = TRUE)
                );

                total_items := total_lectures + total_practices + total_tests;
                completed_items := total_lectures + completed_practices + completed_tests;

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

        # 3. функция: баллы за тест
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION calculate_test_score(p_user_id INTEGER, p_test_id INTEGER, p_attempt_number INTEGER)
            RETURNS INTEGER AS $$
            DECLARE
                total_score INTEGER;
            BEGIN
                SELECT COALESCE(SUM(user_answer.score), 0) INTO total_score
                FROM user_answer
                JOIN question ON user_answer.question_id = question.id
                WHERE question.test_id = p_test_id
                  AND user_answer.user_id = p_user_id
                  AND user_answer.attempt_number = p_attempt_number;
                  
                RETURN total_score;
            EXCEPTION
                WHEN OTHERS THEN
                    RETURN 0;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS calculate_test_score(INTEGER, INTEGER, INTEGER);"
        ),

        # 4. представление: практические задания с порядком лекций 
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE VIEW view_course_practical_assignments AS
            SELECT DISTINCT
                course.id AS course_id,
                course.course_name,
                lecture.id AS lecture_id,
                lecture.lecture_name,
                lecture.lecture_order,
                practical_assignment.id AS practical_assignment_id,
                practical_assignment.practical_assignment_name,
                practical_assignment.practical_assignment_description,
                practical_assignment.assignment_document_path,
                practical_assignment.assignment_criteria,
                practical_assignment.assignment_deadline,
                practical_assignment.grading_type,
                practical_assignment.max_score,
                practical_assignment.is_active
            FROM course
            JOIN lecture ON lecture.course_id = course.id
            JOIN practical_assignment ON practical_assignment.lecture_id = lecture.id
            WHERE course.is_active = TRUE 
            AND lecture.is_active = TRUE 
            AND practical_assignment.is_active = TRUE;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_course_practical_assignments;"
        ),

        # 5. представление: лекции 
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE VIEW view_course_lectures AS
            SELECT DISTINCT
                course.id AS course_id,
                course.course_name,
                lecture.id AS lecture_id,
                lecture.lecture_name,
                lecture.lecture_content,
                lecture.lecture_document_path,
                lecture.lecture_order,
                lecture.is_active
            FROM course
            JOIN lecture ON lecture.course_id = course.id
            WHERE course.is_active = TRUE 
            AND lecture.is_active = TRUE;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_course_lectures;"
        ),

        # 6. представление: тесты с порядком лекций 
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE VIEW view_course_tests AS
            SELECT DISTINCT
                course.id AS course_id,
                course.course_name,
                lecture.id AS lecture_id,
                lecture.lecture_name,
                lecture.lecture_order,
                test.id AS test_id,
                test.test_name,
                test.test_description,
                test.is_final,
                test.max_attempts,
                test.grading_form,
                test.passing_score,
                test.is_active
            FROM course
            JOIN lecture ON lecture.course_id = course.id
            JOIN test ON test.lecture_id = lecture.id
            WHERE course.is_active = TRUE 
            AND lecture.is_active = TRUE 
            AND test.is_active = TRUE;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_course_tests;"
        ),

        # 7. триггер: обратная связь с улучшенной обработкой ошибок
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_feedback_score_or_passed()
            RETURNS TRIGGER AS $$
            DECLARE
                grading_type_value VARCHAR(20);
                assignment_exists BOOLEAN;
            BEGIN
                SELECT EXISTS (
                    SELECT 1 FROM user_practical_assignment
                    WHERE id = NEW.user_practical_assignment_id
                ) INTO assignment_exists;
                
                IF NOT assignment_exists THEN
                    RAISE EXCEPTION 'Задание с ID % не существует', NEW.user_practical_assignment_id;
                END IF;

                SELECT practical_assignment.grading_type INTO grading_type_value
                FROM practical_assignment
                JOIN user_practical_assignment ON practical_assignment.id = user_practical_assignment.practical_assignment_id
                WHERE user_practical_assignment.id = NEW.user_practical_assignment_id;

                IF grading_type_value = 'points' THEN
                    IF NEW.score IS NULL THEN
                        RAISE EXCEPTION 'Для типа оценки ''points'' поле score обязательно для заполнения';
                    END IF;
                    IF NEW.is_passed IS NOT NULL THEN
                        RAISE EXCEPTION 'Для типа оценки ''points'' поле is_passed должно быть NULL';
                    END IF;
                    IF NEW.score < 0 THEN
                        RAISE EXCEPTION 'Оценка не может быть отрицательной';
                    END IF;
                ELSIF grading_type_value = 'pass_fail' THEN
                    IF NEW.is_passed IS NULL THEN
                        RAISE EXCEPTION 'Для типа оценки ''pass_fail'' поле is_passed обязательно для заполнения';
                    END IF;
                    IF NEW.score IS NOT NULL THEN
                        RAISE EXCEPTION 'Для типа оценки ''pass_fail'' поле score должно быть NULL';
                    END IF;
                ELSE
                    RAISE EXCEPTION 'Недопустимый тип оценки: %. Допустимые значения: points, pass_fail', grading_type_value;
                END IF;
                
                RETURN NEW;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trigger_check_feedback ON feedback;
            CREATE TRIGGER trigger_check_feedback
            BEFORE INSERT OR UPDATE ON feedback
            FOR EACH ROW EXECUTE FUNCTION check_feedback_score_or_passed();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trigger_check_feedback ON feedback;
            DROP FUNCTION IF EXISTS check_feedback_score_or_passed();
            """
        ),

        # 8. процедура: завершить курс с транзакцией
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE PROCEDURE update_course_status(p_user_id INTEGER, p_course_id BIGINT)
            AS $$
            DECLARE
                all_practices_completed BOOLEAN;
                all_tests_completed BOOLEAN;
                registration_time TIMESTAMP;
                user_course_exists BOOLEAN;
                course_active BOOLEAN;
            BEGIN

                SELECT EXISTS (
                    SELECT 1 FROM user_course 
                    WHERE user_id = p_user_id AND course_id = p_course_id
                ) INTO user_course_exists;
                
                IF NOT user_course_exists THEN
                    RAISE EXCEPTION 'Пользователь с ID % не записан на курс с ID %', p_user_id, p_course_id;
                END IF;

                SELECT is_active INTO course_active
                FROM course WHERE id = p_course_id;
                
                IF NOT course_active THEN
                    RAISE EXCEPTION 'Курс с ID % не активен', p_course_id;
                END IF;

                SELECT NOT EXISTS(
                    SELECT 1 FROM practical_assignment
                    JOIN lecture ON practical_assignment.lecture_id = lecture.id
                    LEFT JOIN user_practical_assignment ON practical_assignment.id = user_practical_assignment.practical_assignment_id 
                        AND user_practical_assignment.user_id = p_user_id
                    LEFT JOIN feedback ON feedback.user_practical_assignment_id = user_practical_assignment.id
                    WHERE lecture.course_id = p_course_id
                    AND practical_assignment.is_active = TRUE
                    AND (
                        (user_practical_assignment.id IS NULL) OR
                        (practical_assignment.grading_type = 'points' AND (feedback.score IS NULL OR feedback.score < practical_assignment.max_score * 0.6)) OR
                        (practical_assignment.grading_type = 'pass_fail' AND (feedback.is_passed IS NULL OR feedback.is_passed = FALSE))
                    )
                ) INTO all_practices_completed;

                SELECT NOT EXISTS(
                    SELECT 1 FROM test
                    JOIN lecture ON test.lecture_id = lecture.id
                    LEFT JOIN test_result ON test.id = test_result.test_id AND test_result.user_id = p_user_id
                    WHERE lecture.course_id = p_course_id
                    AND test.is_active = TRUE
                    AND (
                        (test_result.id IS NULL) OR
                        (test.grading_form = 'points' AND (test_result.final_score IS NULL OR test_result.final_score < test.passing_score)) OR
                        (test.grading_form = 'pass_fail' AND (test_result.is_passed IS NULL OR test_result.is_passed = FALSE))
                    )
                ) INTO all_tests_completed;

                SELECT user_course.registration_date::TIMESTAMP INTO registration_time
                FROM user_course
                WHERE user_course.user_id = p_user_id AND user_course.course_id = p_course_id;

                IF registration_time IS NULL THEN
                    RAISE EXCEPTION 'Не найдена дата регистрации на курс';
                END IF;

                IF (CURRENT_TIMESTAMP - registration_time) < INTERVAL '1 hour' THEN
                    RAISE EXCEPTION 'Не прошло более часа с момента регистрации на курс';
                END IF;

                IF all_practices_completed AND all_tests_completed THEN
                    UPDATE user_course 
                    SET status_course = TRUE,
                        completion_date = CURRENT_DATE
                    WHERE user_id = p_user_id AND course_id = p_course_id;
                    
                    RAISE NOTICE 'Курс успешно завершен для пользователя %', p_user_id;
                ELSE
                    RAISE EXCEPTION 'Не все задания завершены. Практические: %, Тесты: %', 
                        all_practices_completed, all_tests_completed;
                END IF;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS update_course_status(INTEGER, BIGINT);"
        ),

        # 9. триггер: роль преподавателя с проверкой пользователя
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_teacher_role()
            RETURNS TRIGGER AS $$
            DECLARE
                user_role_name VARCHAR(255);
                user_exists BOOLEAN;
            BEGIN
                SELECT EXISTS(SELECT 1 FROM "user" WHERE id = NEW.teacher_id) INTO user_exists;
                
                IF NOT user_exists THEN
                    RAISE EXCEPTION 'Пользователь с ID % не существует', NEW.teacher_id;
                END IF;

                SELECT role.role_name INTO user_role_name
                FROM "user"
                JOIN role ON "user".role_id = role.id
                WHERE "user".id = NEW.teacher_id;

                IF user_role_name != 'преподаватель' THEN
                    RAISE EXCEPTION 'Пользователь с ID % имеет роль "%". Требуется роль "преподаватель"', 
                        NEW.teacher_id, user_role_name;
                END IF;
                
                RETURN NEW;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trigger_check_teacher_role ON course_teacher;
            CREATE TRIGGER trigger_check_teacher_role
            BEFORE INSERT OR UPDATE ON course_teacher
            FOR EACH ROW EXECUTE FUNCTION check_teacher_role();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trigger_check_teacher_role ON course_teacher;
            DROP FUNCTION IF EXISTS check_teacher_role();
            """
        ),

        # 10. триггер: методист роль с улучшенной проверкой
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_methodist_role()
            RETURNS TRIGGER AS $$
            DECLARE
                user_role_name VARCHAR(255);
                user_exists BOOLEAN;
            BEGIN

                IF NEW.created_by_id IS NOT NULL THEN

                    SELECT EXISTS(SELECT 1 FROM "user" WHERE id = NEW.created_by_id) INTO user_exists;
                    
                    IF NOT user_exists THEN
                        RAISE EXCEPTION 'Пользователь с ID % не существует', NEW.created_by_id;
                    END IF;

                    SELECT role.role_name INTO user_role_name
                    FROM "user"
                    JOIN role ON "user".role_id = role.id
                    WHERE "user".id = NEW.created_by_id;

                    IF user_role_name != 'методист' THEN
                        RAISE EXCEPTION 'Создателем курса может быть только пользователь с ролью "методист". Текущая роль: "%"', 
                            user_role_name;
                    END IF;
                END IF;
                
                RETURN NEW;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trigger_check_methodist_role ON course;
            CREATE TRIGGER trigger_check_methodist_role
            BEFORE INSERT OR UPDATE ON course
            FOR EACH ROW EXECUTE FUNCTION check_methodist_role();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trigger_check_methodist_role ON course;
            DROP FUNCTION IF EXISTS check_methodist_role();
            """
        ),

        # 11. функция: общие баллы курса с обработкой ошибок
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION calculate_total_course_points(p_course_id BIGINT)
            RETURNS INTEGER AS $$
            DECLARE
                total_practice_points INTEGER;
                total_test_points INTEGER;
                course_exists BOOLEAN;
            BEGIN

                SELECT EXISTS(SELECT 1 FROM course WHERE id = p_course_id) INTO course_exists;
                
                IF NOT course_exists THEN
                    RETURN 0;
                END IF;

                SELECT COALESCE(SUM(practical_assignment.max_score), 0) INTO total_practice_points
                FROM practical_assignment
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id 
                  AND practical_assignment.grading_type = 'points'
                  AND practical_assignment.is_active = TRUE;

                SELECT COALESCE(SUM(question.question_score), 0) INTO total_test_points
                FROM question
                JOIN test ON question.test_id = test.id
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id 
                  AND test.is_active = TRUE;

                RETURN total_practice_points + total_test_points;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RETURN 0;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS calculate_total_course_points(BIGINT);"
        ),

        # 12. триггер: результаты теста с улучшенной валидацией
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_test_results_score_or_passed()
            RETURNS TRIGGER AS $$
            DECLARE
                grading_form_value VARCHAR(20);
                test_exists BOOLEAN;
                max_score INTEGER;
            BEGIN
                SELECT EXISTS(SELECT 1 FROM test WHERE id = NEW.test_id) INTO test_exists;
                
                IF NOT test_exists THEN
                    RAISE EXCEPTION 'Тест с ID % не существует', NEW.test_id;
                END IF;

                SELECT test.grading_form INTO grading_form_value
                FROM test WHERE test.id = NEW.test_id;

                IF grading_form_value = 'points' THEN
                    IF NEW.final_score IS NULL THEN
                        RAISE EXCEPTION 'Для формы оценки ''points'' поле final_score обязательно для заполнения';
                    END IF;
                    IF NEW.is_passed IS NOT NULL THEN
                        RAISE EXCEPTION 'Для формы оценки ''points'' поле is_passed должно быть NULL';
                    END IF;
                    SELECT COALESCE(SUM(question.question_score), 0) INTO max_score
                    FROM question
                    WHERE question.test_id = NEW.test_id;
                    
                    IF NEW.final_score < 0 OR NEW.final_score > max_score THEN
                        RAISE EXCEPTION 'Баллы должны быть в диапазоне от 0 до %', max_score;
                    END IF;
                ELSIF grading_form_value = 'pass_fail' THEN
                    IF NEW.is_passed IS NULL THEN
                        RAISE EXCEPTION 'Для формы оценки ''pass_fail'' поле is_passed обязательно для заполнения';
                    END IF;
                    IF NEW.final_score IS NOT NULL THEN
                        RAISE EXCEPTION 'Для формы оценки ''pass_fail'' поле final_score должно быть NULL';
                    END IF;
                ELSE
                    RAISE EXCEPTION 'Недопустимая форма оценки: %. Допустимые значения: points, pass_fail', grading_form_value;
                END IF;
                
                RETURN NEW;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trigger_check_test_results ON test_result;
            CREATE TRIGGER trigger_check_test_results
            BEFORE INSERT OR UPDATE ON test_result
            FOR EACH ROW EXECUTE FUNCTION check_test_results_score_or_passed();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trigger_check_test_results ON test_result;
            DROP FUNCTION IF EXISTS check_test_results_score_or_passed();
            """
        ),

        # 13. триггер: сертификат с проверкой статуса курса
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_status_course_for_certificate()
            RETURNS TRIGGER AS $$
            DECLARE
                course_status BOOLEAN;
                user_course_exists BOOLEAN;
            BEGIN

                SELECT EXISTS(SELECT 1 FROM user_course WHERE id = NEW.user_course_id) INTO user_course_exists;
                
                IF NOT user_course_exists THEN
                    RAISE EXCEPTION 'Запись пользователя на курс с ID % не существует', NEW.user_course_id;
                END IF;

                SELECT user_course.status_course INTO course_status
                FROM user_course WHERE user_course.id = NEW.user_course_id;

                IF NOT course_status THEN
                    RAISE EXCEPTION 'Сертификат не может быть выдан: курс не завершён для записи с ID %', NEW.user_course_id;
                END IF;
                
                RETURN NEW;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trigger_check_status_course ON certificate;
            CREATE TRIGGER trigger_check_status_course
            BEFORE INSERT ON certificate
            FOR EACH ROW EXECUTE FUNCTION check_status_course_for_certificate();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trigger_check_status_course ON certificate;
            DROP FUNCTION IF EXISTS check_status_course_for_certificate();
            """
        ),

        # 14. процедура: назначить преподавателя на курс с проверками
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE PROCEDURE assign_teacher_to_course(
                p_teacher_id INTEGER, 
                p_course_id BIGINT, 
                p_start_date DATE DEFAULT CURRENT_DATE
            )
            AS $$
            DECLARE
                teacher_exists BOOLEAN;
                course_exists BOOLEAN;
                already_assigned BOOLEAN;
            BEGIN

                SELECT EXISTS(
                    SELECT 1 FROM "user" 
                    JOIN role ON "user".role_id = role.id 
                    WHERE "user".id = p_teacher_id AND role.role_name = 'преподаватель'
                ) INTO teacher_exists;
                
                IF NOT teacher_exists THEN
                    RAISE EXCEPTION 'Преподаватель с ID % не существует или не имеет соответствующей роли', p_teacher_id;
                END IF;


                SELECT EXISTS(SELECT 1 FROM course WHERE id = p_course_id) INTO course_exists;
                
                IF NOT course_exists THEN
                    RAISE EXCEPTION 'Курс с ID % не существует', p_course_id;
                END IF;


                SELECT EXISTS(
                    SELECT 1 FROM course_teacher 
                    WHERE teacher_id = p_teacher_id AND course_id = p_course_id
                ) INTO already_assigned;
                
                IF already_assigned THEN
                    RAISE EXCEPTION 'Преподаватель с ID % уже назначен на курс с ID %', p_teacher_id, p_course_id;
                END IF;

                INSERT INTO course_teacher (teacher_id, course_id, start_date)
                VALUES (p_teacher_id, p_course_id, p_start_date);
                
                RAISE NOTICE 'Преподаватель с ID % успешно назначен на курс с ID %', p_teacher_id, p_course_id;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS assign_teacher_to_course(INTEGER, BIGINT, DATE);"
        ),

        # 15. процедура: удалить пользователя с курса с проверками
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE PROCEDURE remove_user_from_course(p_user_id INTEGER, p_course_id BIGINT)
            AS $$
            DECLARE
                enrollment_exists BOOLEAN;
                course_completed BOOLEAN;
            BEGIN

                SELECT EXISTS(
                    SELECT 1 FROM user_course 
                    WHERE user_id = p_user_id AND course_id = p_course_id
                ) INTO enrollment_exists;
                
                IF NOT enrollment_exists THEN
                    RAISE EXCEPTION 'Пользователь с ID % не записан на курс с ID %', p_user_id, p_course_id;
                END IF;

                SELECT status_course INTO course_completed
                FROM user_course 
                WHERE user_id = p_user_id AND course_id = p_course_id;
                
                IF course_completed THEN
                    RAISE EXCEPTION 'Нельзя удалить пользователя с завершенного курса';
                END IF;

                DELETE FROM user_course
                WHERE user_id = p_user_id AND course_id = p_course_id;
                
                RAISE NOTICE 'Пользователь с ID % успешно удален с курса с ID %', p_user_id, p_course_id;
                
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS remove_user_from_course(INTEGER, BIGINT);"
        ),

        # 16. Функция для проверки файлов сдачи 
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_assignment_submission_files()
            RETURNS TRIGGER AS $$
            DECLARE
                total_file_size BIGINT;
                file_count INTEGER;
                max_total_size CONSTANT BIGINT := 100 * 1024 * 1024; -- 100 МБ общий лимит
            BEGIN

                SELECT COUNT(*), COALESCE(SUM(file_size), 0)
                INTO file_count, total_file_size
                FROM assignment_submission_file
                WHERE user_assignment_id = NEW.user_assignment_id;


                IF total_file_size > max_total_size THEN
                    RAISE EXCEPTION 'Общий размер файлов для этой сдачи превышает 100 МБ. Текущий размер: % bytes', total_file_size;
                END IF;

                IF file_count > 10 THEN
                    RAISE EXCEPTION 'Нельзя прикреплять более 10 файлов к одной сдаче';
                END IF;

                RETURN NEW;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trigger_check_assignment_files ON assignment_submission_file;
            CREATE TRIGGER trigger_check_assignment_files
            BEFORE INSERT ON assignment_submission_file
            FOR EACH ROW EXECUTE FUNCTION check_assignment_submission_files();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trigger_check_assignment_files ON assignment_submission_file;
            DROP FUNCTION IF EXISTS check_assignment_submission_files();
            """
        ),

        # 17. представление для отображения сдач с файлами 
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE VIEW view_assignment_submissions AS
            SELECT 
                upa.id as submission_id,
                upa.user_id,
                u.first_name || ' ' || u.last_name as user_name,
                upa.practical_assignment_id,
                pa.practical_assignment_name,
                l.lecture_name,
                c.course_name,
                upa.submission_date,
                upa.attempt_number,
                ast.assignment_status_name as status,
                upa.comment,
                COUNT(af.id) as file_count,
                COALESCE(SUM(af.file_size), 0) as total_size
            FROM user_practical_assignment upa
            JOIN "user" u ON upa.user_id = u.id
            JOIN practical_assignment pa ON upa.practical_assignment_id = pa.id
            JOIN lecture l ON pa.lecture_id = l.id
            JOIN course c ON l.course_id = c.id
            JOIN assignment_status ast ON upa.submission_status_id = ast.id
            LEFT JOIN assignment_submission_file af ON upa.id = af.user_assignment_id
            GROUP BY 
                upa.id, u.first_name, u.last_name, pa.practical_assignment_name, 
                l.lecture_name, c.course_name, ast.assignment_status_name
            ORDER BY upa.submission_date DESC;
            """,
            reverse_sql="DROP VIEW IF EXISTS view_assignment_submissions;"
        ),
    ]