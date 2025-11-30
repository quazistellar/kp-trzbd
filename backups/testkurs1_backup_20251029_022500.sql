--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3
-- Dumped by pg_dump version 16.3

-- Started on 2025-10-29 02:25:01

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 302 (class 1255 OID 125153)
-- Name: assign_teacher_to_course(integer, bigint, date); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.assign_teacher_to_course(IN p_teacher_id integer, IN p_course_id bigint, IN p_start_date date DEFAULT CURRENT_DATE)
    LANGUAGE plpgsql
    AS $$
            BEGIN
                INSERT INTO unireax_main_courseteacher (teacher_id, course_id, start_date)
                VALUES (p_teacher_id, p_course_id, p_start_date);
            END;
            $$;


ALTER PROCEDURE public.assign_teacher_to_course(IN p_teacher_id integer, IN p_course_id bigint, IN p_start_date date) OWNER TO postgres;

--
-- TOC entry 282 (class 1255 OID 125125)
-- Name: calculate_course_completion(integer, bigint); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_course_completion(p_user_id integer, p_course_id bigint) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
            DECLARE
                total_lectures INTEGER;
                total_practices INTEGER;
                completed_practices INTEGER;
                total_tests INTEGER;
                completed_tests INTEGER;
                total_items INTEGER;
                completed_items INTEGER;
            BEGIN
                SELECT COUNT(*) INTO total_lectures
                FROM unireax_main_lecture
                WHERE unireax_main_lecture.course_id = p_course_id;

                SELECT COUNT(*) INTO total_practices
                FROM unireax_main_practicalassignment
                JOIN unireax_main_lecture ON unireax_main_practicalassignment.lecture_id = unireax_main_lecture.id
                WHERE unireax_main_lecture.course_id = p_course_id;

                SELECT COUNT(*) INTO completed_practices
                FROM unireax_main_userpracticalassignment
                JOIN unireax_main_practicalassignment ON unireax_main_userpracticalassignment.practical_assignment_id = unireax_main_practicalassignment.id
                JOIN unireax_main_lecture ON unireax_main_practicalassignment.lecture_id = unireax_main_lecture.id
                JOIN unireax_main_assignmentstatus ON unireax_main_userpracticalassignment.submission_status_id = unireax_main_assignmentstatus.id
                WHERE unireax_main_lecture.course_id = p_course_id
                  AND unireax_main_userpracticalassignment.user_id = p_user_id
                  AND unireax_main_assignmentstatus.assignment_status_name = 'completed';

                SELECT COUNT(*) INTO total_tests
                FROM unireax_main_test
                JOIN unireax_main_lecture ON unireax_main_test.lecture_id = unireax_main_lecture.id
                WHERE unireax_main_lecture.course_id = p_course_id;

                SELECT COUNT(*) INTO completed_tests
                FROM unireax_main_testresult
                JOIN unireax_main_test ON unireax_main_testresult.test_id = unireax_main_test.id
                JOIN unireax_main_lecture ON unireax_main_test.lecture_id = unireax_main_lecture.id
                WHERE unireax_main_lecture.course_id = p_course_id
                  AND unireax_main_testresult.user_id = p_user_id
                  AND (
                    (unireax_main_test.grading_form = 'points' AND unireax_main_testresult.final_score >= unireax_main_test.passing_score)
                    OR (unireax_main_test.grading_form = 'pass_fail' AND unireax_main_testresult.is_passed = TRUE)
                  );

                total_items := total_lectures + total_practices + total_tests;
                completed_items := total_lectures + completed_practices + completed_tests;

                IF total_items = 0 THEN
                    RETURN 0.00;
                END IF;

                RETURN (completed_items::DECIMAL / total_items * 100)::DECIMAL(5,2);
            END;
            $$;


ALTER FUNCTION public.calculate_course_completion(p_user_id integer, p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 281 (class 1255 OID 125124)
-- Name: calculate_course_rating(bigint); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_course_rating(p_course_id bigint) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
            BEGIN
                RETURN COALESCE(
                    (SELECT AVG(unireax_main_review.rating)::DECIMAL(3,2)
                     FROM unireax_main_review
                     WHERE unireax_main_review.course_id = p_course_id),
                    0.00
                );
            END;
            $$;


ALTER FUNCTION public.calculate_course_rating(p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 283 (class 1255 OID 125126)
-- Name: calculate_test_score(integer, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_test_score(p_user_id integer, p_test_id integer, p_attempt_number integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
            BEGIN
                RETURN COALESCE(
                    (SELECT SUM(unireax_main_useranswer.score)
                     FROM unireax_main_useranswer
                     JOIN unireax_main_question ON unireax_main_useranswer.question_id = unireax_main_question.id
                     WHERE unireax_main_question.test_id = p_test_id
                       AND unireax_main_useranswer.user_id = p_user_id
                       AND unireax_main_useranswer.attempt_number = p_attempt_number),
                    0
                );
            END;
            $$;


ALTER FUNCTION public.calculate_test_score(p_user_id integer, p_test_id integer, p_attempt_number integer) OWNER TO postgres;

--
-- TOC entry 299 (class 1255 OID 125148)
-- Name: calculate_total_course_points(bigint); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_total_course_points(p_course_id bigint) RETURNS integer
    LANGUAGE plpgsql
    AS $$
            DECLARE
                total_practice_points INTEGER;
                total_test_points INTEGER;
            BEGIN
                SELECT COALESCE(SUM(unireax_main_practicalassignment.max_score), 0) INTO total_practice_points
                FROM unireax_main_practicalassignment
                JOIN unireax_main_lecture ON unireax_main_practicalassignment.lecture_id = unireax_main_lecture.id
                WHERE unireax_main_lecture.course_id = p_course_id AND unireax_main_practicalassignment.grading_type = 'points';

                SELECT COALESCE(SUM(unireax_main_question.question_score), 0) INTO total_test_points
                FROM unireax_main_question
                JOIN unireax_main_test ON unireax_main_question.test_id = unireax_main_test.id
                JOIN unireax_main_lecture ON unireax_main_test.lecture_id = unireax_main_lecture.id
                WHERE unireax_main_lecture.course_id = p_course_id;

                RETURN total_practice_points + total_test_points;
            END;
            $$;


ALTER FUNCTION public.calculate_total_course_points(p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 295 (class 1255 OID 125141)
-- Name: check_feedback_score_or_passed(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_feedback_score_or_passed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                grading_type_value VARCHAR(20);
            BEGIN
                SELECT unireax_main_practicalassignment.grading_type INTO grading_type_value
                FROM unireax_main_practicalassignment
                JOIN unireax_main_userpracticalassignment ON unireax_main_practicalassignment.id = unireax_main_userpracticalassignment.practical_assignment_id
                WHERE unireax_main_userpracticalassignment.id = NEW.user_practical_assignment_id;

                IF grading_type_value = 'points' THEN
                    IF NEW.score IS NULL OR NEW.is_passed IS NOT NULL THEN
                        RAISE EXCEPTION 'Для grading_type ''points'' score должен быть заполнен, а is_passed должен быть NULL';
                    END IF;
                ELSIF grading_type_value = 'pass_fail' THEN
                    IF NEW.is_passed IS NULL OR NEW.score IS NOT NULL THEN
                        RAISE EXCEPTION 'Для grading_type ''pass_fail'' is_passed должен быть заполнен, а score должен быть NULL';
                    END IF;
                ELSE
                    RAISE EXCEPTION 'Недопустимое значение grading_type: %', grading_type_value;
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_feedback_score_or_passed() OWNER TO postgres;

--
-- TOC entry 298 (class 1255 OID 125146)
-- Name: check_methodist_role(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_methodist_role() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM unireax_main_user
                    JOIN unireax_main_role ON unireax_main_user.role_id = unireax_main_role.id
                    WHERE unireax_main_user.id = NEW.created_by_id AND unireax_main_role.role_name = 'методист'
                ) THEN
                    RAISE EXCEPTION 'created_by must reference a user with role "методист"';
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_methodist_role() OWNER TO postgres;

--
-- TOC entry 301 (class 1255 OID 125151)
-- Name: check_status_course_for_certificate(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_status_course_for_certificate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                course_status BOOLEAN;
            BEGIN
                SELECT unireax_main_usercourse.status_course INTO course_status
                FROM unireax_main_usercourse WHERE unireax_main_usercourse.id = NEW.user_course_id;

                IF NOT course_status THEN
                    RAISE EXCEPTION 'Сертификат не может быть выдан: курс не завершён для user_course_id %', NEW.user_course_id;
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_status_course_for_certificate() OWNER TO postgres;

--
-- TOC entry 297 (class 1255 OID 125144)
-- Name: check_teacher_role(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_teacher_role() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM unireax_main_user
                    JOIN unireax_main_role ON unireax_main_user.role_id = unireax_main_role.id
                    WHERE unireax_main_user.id = NEW.teacher_id AND unireax_main_role.role_name = 'teacher'
                ) THEN
                    RAISE EXCEPTION 'teacher_id must reference a user with role "teacher"';
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_teacher_role() OWNER TO postgres;

--
-- TOC entry 300 (class 1255 OID 125149)
-- Name: check_test_results_score_or_passed(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_test_results_score_or_passed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                grading_form_value VARCHAR(20);
            BEGIN
                SELECT unireax_main_test.grading_form INTO grading_form_value
                FROM unireax_main_test WHERE unireax_main_test.id = NEW.test_id;

                IF grading_form_value = 'points' THEN
                    IF NEW.final_score IS NULL OR NEW.is_passed IS NOT NULL THEN
                        RAISE EXCEPTION 'Для grading_form ''points'' final_score должен быть заполнен, а is_passed должен быть NULL';
                    END IF;
                ELSIF grading_form_value = 'pass_fail' THEN
                    IF NEW.is_passed IS NULL OR NEW.final_score IS NOT NULL THEN
                        RAISE EXCEPTION 'Для grading_form ''pass_fail'' is_passed должен быть заполнен, а final_score должен быть NULL';
                    END IF;
                ELSE
                    RAISE EXCEPTION 'Недопустимое значение grading_form: %', grading_form_value;
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_test_results_score_or_passed() OWNER TO postgres;

--
-- TOC entry 303 (class 1255 OID 125154)
-- Name: remove_user_from_course(integer, bigint); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.remove_user_from_course(IN p_user_id integer, IN p_course_id bigint)
    LANGUAGE plpgsql
    AS $$
            BEGIN
                DELETE FROM unireax_main_usercourse
                WHERE unireax_main_usercourse.user_id = p_user_id AND unireax_main_usercourse.course_id = p_course_id;
            END;
            $$;


ALTER PROCEDURE public.remove_user_from_course(IN p_user_id integer, IN p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 296 (class 1255 OID 125143)
-- Name: update_course_status(integer, bigint); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.update_course_status(IN p_user_id integer, IN p_course_id bigint)
    LANGUAGE plpgsql
    AS $$
            DECLARE
                all_practices_completed BOOLEAN;
                all_tests_completed BOOLEAN;
                registration_time TIMESTAMP;
            BEGIN
                SELECT NOT EXISTS(
                    SELECT 1 FROM unireax_main_practicalassignment
                    JOIN unireax_main_lecture ON unireax_main_practicalassignment.lecture_id = unireax_main_lecture.id
                    LEFT JOIN unireax_main_userpracticalassignment ON unireax_main_practicalassignment.id = unireax_main_userpracticalassignment.practical_assignment_id AND unireax_main_userpracticalassignment.user_id = p_user_id
                    LEFT JOIN unireax_main_feedback ON unireax_main_feedback.user_practical_assignment_id = unireax_main_userpracticalassignment.id
                    WHERE unireax_main_lecture.course_id = p_course_id
                    AND (
                        (unireax_main_userpracticalassignment.id IS NULL) OR
                        (unireax_main_practicalassignment.grading_type = 'points' AND (unireax_main_feedback.score IS NULL OR unireax_main_feedback.score <= 2)) OR
                        (unireax_main_practicalassignment.grading_type = 'pass_fail' AND (unireax_main_feedback.is_passed IS NULL OR unireax_main_feedback.is_passed = FALSE))
                    )
                ) INTO all_practices_completed;

                SELECT NOT EXISTS(
                    SELECT 1 FROM unireax_main_test
                    JOIN unireax_main_lecture ON unireax_main_test.lecture_id = unireax_main_lecture.id
                    LEFT JOIN unireax_main_testresult ON unireax_main_test.id = unireax_main_testresult.test_id AND unireax_main_testresult.user_id = p_user_id
                    WHERE unireax_main_lecture.course_id = p_course_id
                    AND (
                        (unireax_main_testresult.id IS NULL) OR
                        (unireax_main_test.grading_form = 'points' AND (unireax_main_testresult.final_score IS NULL OR unireax_main_testresult.final_score < unireax_main_test.passing_score)) OR
                        (unireax_main_test.grading_form = 'pass_fail' AND (unireax_main_testresult.is_passed IS NULL OR unireax_main_testresult.is_passed = FALSE))
                    )
                ) INTO all_tests_completed;

                SELECT unireax_main_usercourse.registration_date::TIMESTAMP INTO registration_time
                FROM unireax_main_usercourse
                WHERE unireax_main_usercourse.user_id = p_user_id AND unireax_main_usercourse.course_id = p_course_id;

                IF registration_time IS NULL OR (CURRENT_TIMESTAMP - registration_time) < INTERVAL '1 hour' THEN
                    RAISE EXCEPTION 'Не прошло более часа с регистрации';
                END IF;

                IF all_practices_completed AND all_tests_completed THEN
                    UPDATE unireax_main_usercourse SET status_course = TRUE
                    WHERE unireax_main_usercourse.user_id = p_user_id AND unireax_main_usercourse.course_id = p_course_id;
                ELSE
                    RAISE EXCEPTION 'Не все задания завершены';
                END IF;
            END;
            $$;


ALTER PROCEDURE public.update_course_status(IN p_user_id integer, IN p_course_id bigint) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 92368)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 92367)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 224 (class 1259 OID 92376)
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 92375)
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 220 (class 1259 OID 92362)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 92361)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 276 (class 1259 OID 92827)
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id bigint NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO postgres;

--
-- TOC entry 275 (class 1259 OID 92826)
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 218 (class 1259 OID 92354)
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 92353)
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 216 (class 1259 OID 92346)
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO postgres;

--
-- TOC entry 215 (class 1259 OID 92345)
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 277 (class 1259 OID 92847)
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 92408)
-- Name: unireax_main_answertype; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_answertype (
    id bigint NOT NULL,
    answer_type_name character varying(50) NOT NULL,
    answer_type_description text
);


ALTER TABLE public.unireax_main_answertype OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 92407)
-- Name: unireax_main_answertype_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_answertype ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_answertype_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 228 (class 1259 OID 92418)
-- Name: unireax_main_assignmentstatus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_assignmentstatus (
    id bigint NOT NULL,
    assignment_status_name character varying(255) NOT NULL
);


ALTER TABLE public.unireax_main_assignmentstatus OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 92417)
-- Name: unireax_main_assignmentstatus_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_assignmentstatus ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_assignmentstatus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 260 (class 1259 OID 92545)
-- Name: unireax_main_certificate; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_certificate (
    id bigint NOT NULL,
    certificate_number character varying(255) NOT NULL,
    issue_date date NOT NULL,
    certificate_file_path character varying(255),
    user_course_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_certificate OWNER TO postgres;

--
-- TOC entry 259 (class 1259 OID 92544)
-- Name: unireax_main_certificate_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_certificate ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_certificate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 252 (class 1259 OID 92510)
-- Name: unireax_main_choiceoption; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_choiceoption (
    id bigint NOT NULL,
    option_text text NOT NULL,
    is_correct boolean NOT NULL,
    question_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_choiceoption OWNER TO postgres;

--
-- TOC entry 251 (class 1259 OID 92509)
-- Name: unireax_main_choiceoption_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_choiceoption ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_choiceoption_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 242 (class 1259 OID 92470)
-- Name: unireax_main_course; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_course (
    id bigint NOT NULL,
    course_name character varying(255) NOT NULL,
    course_description text,
    course_price numeric(10,2),
    course_photo_path character varying(100),
    has_certificate boolean NOT NULL,
    course_max_places integer,
    course_hours integer NOT NULL,
    is_completed boolean NOT NULL,
    code_room character varying(255),
    created_by_id bigint NOT NULL,
    course_category_id bigint NOT NULL,
    course_type_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.unireax_main_course OWNER TO postgres;

--
-- TOC entry 241 (class 1259 OID 92469)
-- Name: unireax_main_course_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_course ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_course_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 230 (class 1259 OID 92426)
-- Name: unireax_main_coursecategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_coursecategory (
    id bigint NOT NULL,
    course_category_name character varying(255) NOT NULL
);


ALTER TABLE public.unireax_main_coursecategory OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 92425)
-- Name: unireax_main_coursecategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_coursecategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_coursecategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 266 (class 1259 OID 92573)
-- Name: unireax_main_courseteacher; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_courseteacher (
    id bigint NOT NULL,
    start_date date NOT NULL,
    course_id bigint NOT NULL,
    teacher_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.unireax_main_courseteacher OWNER TO postgres;

--
-- TOC entry 265 (class 1259 OID 92572)
-- Name: unireax_main_courseteacher_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_courseteacher ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_courseteacher_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 232 (class 1259 OID 92432)
-- Name: unireax_main_coursetype; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_coursetype (
    id bigint NOT NULL,
    course_type_name character varying(255) NOT NULL,
    course_type_description text
);


ALTER TABLE public.unireax_main_coursetype OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 92431)
-- Name: unireax_main_coursetype_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_coursetype ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_coursetype_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 264 (class 1259 OID 92563)
-- Name: unireax_main_feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_feedback (
    id bigint NOT NULL,
    score integer,
    is_passed boolean,
    comment_feedback text,
    user_practical_assignment_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_feedback OWNER TO postgres;

--
-- TOC entry 263 (class 1259 OID 92562)
-- Name: unireax_main_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_feedback ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 244 (class 1259 OID 92478)
-- Name: unireax_main_lecture; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_lecture (
    id bigint NOT NULL,
    lecture_name character varying(255) NOT NULL,
    lecture_content text NOT NULL,
    lecture_document_path character varying(255),
    lecture_order integer NOT NULL,
    course_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.unireax_main_lecture OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 92477)
-- Name: unireax_main_lecture_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_lecture ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_lecture_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 250 (class 1259 OID 92502)
-- Name: unireax_main_matchingpair; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_matchingpair (
    id bigint NOT NULL,
    left_text text NOT NULL,
    right_text text NOT NULL,
    question_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_matchingpair OWNER TO postgres;

--
-- TOC entry 249 (class 1259 OID 92501)
-- Name: unireax_main_matchingpair_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_matchingpair ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_matchingpair_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 246 (class 1259 OID 92486)
-- Name: unireax_main_practicalassignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_practicalassignment (
    id bigint NOT NULL,
    practical_assignment_name character varying(255) NOT NULL,
    practical_assignment_description text NOT NULL,
    assignment_document_path character varying(255),
    assignment_criteria text,
    assignment_deadline date NOT NULL,
    grading_type character varying(20) NOT NULL,
    max_score integer,
    lecture_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.unireax_main_practicalassignment OWNER TO postgres;

--
-- TOC entry 245 (class 1259 OID 92485)
-- Name: unireax_main_practicalassignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_practicalassignment ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_practicalassignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 248 (class 1259 OID 92494)
-- Name: unireax_main_question; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_question (
    id bigint NOT NULL,
    question_text text NOT NULL,
    question_score integer NOT NULL,
    correct_text text,
    question_order integer NOT NULL,
    answer_type_id bigint NOT NULL,
    test_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_question OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 92493)
-- Name: unireax_main_question_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_question ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_question_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 268 (class 1259 OID 92579)
-- Name: unireax_main_review; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_review (
    id bigint NOT NULL,
    review_text text NOT NULL,
    rating integer NOT NULL,
    publish_date timestamp with time zone NOT NULL,
    comment_review text,
    course_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_review OWNER TO postgres;

--
-- TOC entry 267 (class 1259 OID 92578)
-- Name: unireax_main_review_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_review ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 234 (class 1259 OID 92440)
-- Name: unireax_main_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_role (
    id bigint NOT NULL,
    role_name character varying(255) NOT NULL
);


ALTER TABLE public.unireax_main_role OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 92439)
-- Name: unireax_main_role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_role ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 254 (class 1259 OID 92518)
-- Name: unireax_main_test; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_test (
    id bigint NOT NULL,
    test_name character varying(255) NOT NULL,
    test_description text,
    is_final boolean NOT NULL,
    max_attempts integer,
    grading_form character varying(20) NOT NULL,
    passing_score integer,
    lecture_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.unireax_main_test OWNER TO postgres;

--
-- TOC entry 253 (class 1259 OID 92517)
-- Name: unireax_main_test_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_test ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_test_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 270 (class 1259 OID 92587)
-- Name: unireax_main_testresult; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_testresult (
    id bigint NOT NULL,
    completion_date timestamp with time zone NOT NULL,
    final_score integer,
    is_passed boolean,
    attempt_number integer NOT NULL,
    test_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_testresult OWNER TO postgres;

--
-- TOC entry 269 (class 1259 OID 92586)
-- Name: unireax_main_testresult_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_testresult ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_testresult_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 236 (class 1259 OID 92448)
-- Name: unireax_main_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_user (
    id bigint NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    is_verified boolean NOT NULL,
    profile_theme character varying(255),
    educational_institution character varying(255),
    role_id bigint,
    certificat_from_the_place_of_work_path character varying(255),
    "position" character varying(150)
);


ALTER TABLE public.unireax_main_user OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 92458)
-- Name: unireax_main_user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_user_groups (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.unireax_main_user_groups OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 92457)
-- Name: unireax_main_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 235 (class 1259 OID 92447)
-- Name: unireax_main_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 240 (class 1259 OID 92464)
-- Name: unireax_main_user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_user_user_permissions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.unireax_main_user_user_permissions OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 92463)
-- Name: unireax_main_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 256 (class 1259 OID 92531)
-- Name: unireax_main_useranswer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_useranswer (
    id bigint NOT NULL,
    answer_text text,
    answer_date timestamp with time zone NOT NULL,
    attempt_number integer NOT NULL,
    score integer,
    question_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_useranswer OWNER TO postgres;

--
-- TOC entry 255 (class 1259 OID 92530)
-- Name: unireax_main_useranswer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_useranswer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_useranswer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 258 (class 1259 OID 92539)
-- Name: unireax_main_usercourse; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_usercourse (
    id bigint NOT NULL,
    registration_date date NOT NULL,
    status_course boolean NOT NULL,
    payment_date date,
    completion_date date,
    course_price numeric(10,2),
    course_id bigint NOT NULL,
    user_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.unireax_main_usercourse OWNER TO postgres;

--
-- TOC entry 257 (class 1259 OID 92538)
-- Name: unireax_main_usercourse_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_usercourse ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_usercourse_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 272 (class 1259 OID 92593)
-- Name: unireax_main_usermatchinganswer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_usermatchinganswer (
    id bigint NOT NULL,
    user_selected_right_text text NOT NULL,
    matching_pair_id bigint NOT NULL,
    user_answer_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_usermatchinganswer OWNER TO postgres;

--
-- TOC entry 271 (class 1259 OID 92592)
-- Name: unireax_main_usermatchinganswer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_usermatchinganswer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_usermatchinganswer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 262 (class 1259 OID 92557)
-- Name: unireax_main_userpracticalassignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_userpracticalassignment (
    id bigint NOT NULL,
    submission_file_path character varying(255),
    submission_date timestamp with time zone,
    attempt_number integer NOT NULL,
    practical_assignment_id bigint NOT NULL,
    submission_status_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_userpracticalassignment OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 92556)
-- Name: unireax_main_userpracticalassignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_userpracticalassignment ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_userpracticalassignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 274 (class 1259 OID 92601)
-- Name: unireax_main_userselectedchoice; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unireax_main_userselectedchoice (
    id bigint NOT NULL,
    choice_option_id bigint NOT NULL,
    user_answer_id bigint NOT NULL
);


ALTER TABLE public.unireax_main_userselectedchoice OWNER TO postgres;

--
-- TOC entry 273 (class 1259 OID 92600)
-- Name: unireax_main_userselectedchoice_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.unireax_main_userselectedchoice ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.unireax_main_userselectedchoice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 279 (class 1259 OID 125132)
-- Name: view_course_lectures; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_course_lectures AS
 SELECT unireax_main_course.id AS course_id,
    unireax_main_course.course_name,
    unireax_main_lecture.id AS lecture_id,
    unireax_main_lecture.lecture_name,
    unireax_main_lecture.lecture_content,
    unireax_main_lecture.lecture_document_path,
    unireax_main_lecture.lecture_order
   FROM (public.unireax_main_course
     JOIN public.unireax_main_lecture ON ((unireax_main_lecture.course_id = unireax_main_course.id)));


ALTER VIEW public.view_course_lectures OWNER TO postgres;

--
-- TOC entry 278 (class 1259 OID 125127)
-- Name: view_course_practical_assignments; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_course_practical_assignments AS
 SELECT unireax_main_course.id AS course_id,
    unireax_main_course.course_name,
    unireax_main_lecture.id AS lecture_id,
    unireax_main_lecture.lecture_name,
    unireax_main_practicalassignment.id AS practical_assignment_id,
    unireax_main_practicalassignment.practical_assignment_name,
    unireax_main_practicalassignment.practical_assignment_description,
    unireax_main_practicalassignment.assignment_document_path,
    unireax_main_practicalassignment.assignment_criteria,
    unireax_main_practicalassignment.assignment_deadline,
    unireax_main_practicalassignment.grading_type,
    unireax_main_practicalassignment.max_score
   FROM ((public.unireax_main_course
     JOIN public.unireax_main_lecture ON ((unireax_main_lecture.course_id = unireax_main_course.id)))
     JOIN public.unireax_main_practicalassignment ON ((unireax_main_practicalassignment.lecture_id = unireax_main_lecture.id)));


ALTER VIEW public.view_course_practical_assignments OWNER TO postgres;

--
-- TOC entry 280 (class 1259 OID 125136)
-- Name: view_course_tests; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_course_tests AS
 SELECT unireax_main_course.id AS course_id,
    unireax_main_course.course_name,
    unireax_main_lecture.id AS lecture_id,
    unireax_main_lecture.lecture_name,
    unireax_main_test.id AS test_id,
    unireax_main_test.test_name,
    unireax_main_test.test_description,
    unireax_main_test.is_final,
    unireax_main_test.max_attempts,
    unireax_main_test.grading_form,
    unireax_main_test.passing_score,
    unireax_main_question.id AS question_id,
    unireax_main_question.question_text,
    unireax_main_question.answer_type_id,
    unireax_main_answertype.answer_type_name,
    unireax_main_question.question_score,
    unireax_main_question.correct_text,
    unireax_main_question.question_order,
    unireax_main_choiceoption.id AS choice_option_id,
    unireax_main_choiceoption.option_text,
    unireax_main_choiceoption.is_correct,
    unireax_main_matchingpair.id AS matching_pair_id,
    unireax_main_matchingpair.left_text,
    unireax_main_matchingpair.right_text
   FROM ((((((public.unireax_main_course
     JOIN public.unireax_main_lecture ON ((unireax_main_lecture.course_id = unireax_main_course.id)))
     JOIN public.unireax_main_test ON ((unireax_main_test.lecture_id = unireax_main_lecture.id)))
     JOIN public.unireax_main_question ON ((unireax_main_question.test_id = unireax_main_test.id)))
     JOIN public.unireax_main_answertype ON ((unireax_main_question.answer_type_id = unireax_main_answertype.id)))
     LEFT JOIN public.unireax_main_choiceoption ON ((unireax_main_choiceoption.question_id = unireax_main_question.id)))
     LEFT JOIN public.unireax_main_matchingpair ON ((unireax_main_matchingpair.question_id = unireax_main_question.id)));


ALTER VIEW public.view_course_tests OWNER TO postgres;

--
-- TOC entry 5159 (class 0 OID 92368)
-- Dependencies: 222
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- TOC entry 5161 (class 0 OID 92376)
-- Dependencies: 224
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- TOC entry 5157 (class 0 OID 92362)
-- Dependencies: 220
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add content type	4	add_contenttype
14	Can change content type	4	change_contenttype
15	Can delete content type	4	delete_contenttype
16	Can view content type	4	view_contenttype
17	Can add session	5	add_session
18	Can change session	5	change_session
19	Can delete session	5	delete_session
20	Can view session	5	view_session
21	Can add Тип ответа	6	add_answertype
22	Can change Тип ответа	6	change_answertype
23	Can delete Тип ответа	6	delete_answertype
24	Can view Тип ответа	6	view_answertype
25	Can add Статус задания	7	add_assignmentstatus
26	Can change Статус задания	7	change_assignmentstatus
27	Can delete Статус задания	7	delete_assignmentstatus
28	Can view Статус задания	7	view_assignmentstatus
29	Can add Категория курса	8	add_coursecategory
30	Can change Категория курса	8	change_coursecategory
31	Can delete Категория курса	8	delete_coursecategory
32	Can view Категория курса	8	view_coursecategory
33	Can add Тип курса	9	add_coursetype
34	Can change Тип курса	9	change_coursetype
35	Can delete Тип курса	9	delete_coursetype
36	Can view Тип курса	9	view_coursetype
37	Can add Роль	10	add_role
38	Can change Роль	10	change_role
39	Can delete Роль	10	delete_role
40	Can view Роль	10	view_role
41	Can add Пользователь	11	add_user
42	Can change Пользователь	11	change_user
43	Can delete Пользователь	11	delete_user
44	Can view Пользователь	11	view_user
45	Can add Курс	12	add_course
46	Can change Курс	12	change_course
47	Can delete Курс	12	delete_course
48	Can view Курс	12	view_course
49	Can add Лекция	13	add_lecture
50	Can change Лекция	13	change_lecture
51	Can delete Лекция	13	delete_lecture
52	Can view Лекция	13	view_lecture
53	Can add Практическое задание	14	add_practicalassignment
54	Can change Практическое задание	14	change_practicalassignment
55	Can delete Практическое задание	14	delete_practicalassignment
56	Can view Практическое задание	14	view_practicalassignment
57	Can add Вопрос	15	add_question
58	Can change Вопрос	15	change_question
59	Can delete Вопрос	15	delete_question
60	Can view Вопрос	15	view_question
61	Can add Пара соответствия	16	add_matchingpair
62	Can change Пара соответствия	16	change_matchingpair
63	Can delete Пара соответствия	16	delete_matchingpair
64	Can view Пара соответствия	16	view_matchingpair
65	Can add Вариант ответа	17	add_choiceoption
66	Can change Вариант ответа	17	change_choiceoption
67	Can delete Вариант ответа	17	delete_choiceoption
68	Can view Вариант ответа	17	view_choiceoption
69	Can add Тест	18	add_test
70	Can change Тест	18	change_test
71	Can delete Тест	18	delete_test
72	Can view Тест	18	view_test
73	Can add Ответ пользователя	19	add_useranswer
74	Can change Ответ пользователя	19	change_useranswer
75	Can delete Ответ пользователя	19	delete_useranswer
76	Can view Ответ пользователя	19	view_useranswer
77	Can add Пользователь на курсе	20	add_usercourse
78	Can change Пользователь на курсе	20	change_usercourse
79	Can delete Пользователь на курсе	20	delete_usercourse
80	Can view Пользователь на курсе	20	view_usercourse
81	Can add Сертификат	21	add_certificate
82	Can change Сертификат	21	change_certificate
83	Can delete Сертификат	21	delete_certificate
84	Can view Сертификат	21	view_certificate
85	Can add Сдача практического задания	22	add_userpracticalassignment
86	Can change Сдача практического задания	22	change_userpracticalassignment
87	Can delete Сдача практического задания	22	delete_userpracticalassignment
88	Can view Сдача практического задания	22	view_userpracticalassignment
89	Can add Обратная связь	23	add_feedback
90	Can change Обратная связь	23	change_feedback
91	Can delete Обратная связь	23	delete_feedback
92	Can view Обратная связь	23	view_feedback
93	Can add Преподаватель курса	24	add_courseteacher
94	Can change Преподаватель курса	24	change_courseteacher
95	Can delete Преподаватель курса	24	delete_courseteacher
96	Can view Преподаватель курса	24	view_courseteacher
97	Can add Отзыв	25	add_review
98	Can change Отзыв	25	change_review
99	Can delete Отзыв	25	delete_review
100	Can view Отзыв	25	view_review
101	Can add Результат теста	26	add_testresult
102	Can change Результат теста	26	change_testresult
103	Can delete Результат теста	26	delete_testresult
104	Can view Результат теста	26	view_testresult
105	Can add Ответ на сопоставление	27	add_usermatchinganswer
106	Can change Ответ на сопоставление	27	change_usermatchinganswer
107	Can delete Ответ на сопоставление	27	delete_usermatchinganswer
108	Can view Ответ на сопоставление	27	view_usermatchinganswer
109	Can add Выбранный вариант	28	add_userselectedchoice
110	Can change Выбранный вариант	28	change_userselectedchoice
111	Can delete Выбранный вариант	28	delete_userselectedchoice
112	Can view Выбранный вариант	28	view_userselectedchoice
113	Can add view course lectures	29	add_viewcourselectures
114	Can change view course lectures	29	change_viewcourselectures
115	Can delete view course lectures	29	delete_viewcourselectures
116	Can view view course lectures	29	view_viewcourselectures
117	Can add view course practical assignments	30	add_viewcoursepracticalassignments
118	Can change view course practical assignments	30	change_viewcoursepracticalassignments
119	Can delete view course practical assignments	30	delete_viewcoursepracticalassignments
120	Can view view course practical assignments	30	view_viewcoursepracticalassignments
121	Can add view course tests	31	add_viewcoursetests
122	Can change view course tests	31	change_viewcoursetests
123	Can delete view course tests	31	delete_viewcoursetests
124	Can view view course tests	31	view_viewcoursetests
\.


--
-- TOC entry 5213 (class 0 OID 92827)
-- Dependencies: 276
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
1	2025-10-06 12:52:03.921759+03	1	Методист	1	[{"added": {}}]	10	1
2	2025-10-06 12:52:13.007639+03	2	Администратор	1	[{"added": {}}]	10	1
3	2025-10-06 12:52:17.46685+03	3	Преподаватель	1	[{"added": {}}]	10	1
4	2025-10-06 12:54:25.995636+03	4	Слушатель курсов	1	[{"added": {}}]	10	1
5	2025-10-06 13:12:30.660534+03	2	Методистов Методист	1	[{"added": {}}]	11	1
6	2025-10-06 13:15:25.837316+03	1	Информационные технологии	1	[{"added": {}}]	8	1
7	2025-10-06 13:15:59.609981+03	1	Образовательная программа	1	[{"added": {}}]	9	1
8	2025-10-06 13:19:07.869141+03	1	методист	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
9	2025-10-06 13:19:31.345231+03	1	Основы программирования на Java	1	[{"added": {}}]	12	1
10	2025-10-06 14:01:19.146208+03	2	Разработка веб-приложений с использованием Python и фреймворка Django	1	[{"added": {}}]	12	1
11	2025-10-06 14:02:31.607031+03	2	Физика	1	[{"added": {}}]	8	1
12	2025-10-06 14:03:12.12008+03	3	Физика	1	[{"added": {}}]	12	1
13	2025-10-06 14:10:48.054656+03	1	Основы программирования на Java	2	[{"changed": {"fields": ["\\u041f\\u0443\\u0442\\u044c \\u043a \\u0444\\u043e\\u0442\\u043e \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
14	2025-10-15 10:44:18.928928+03	3	Квантовая физика в теории и задачах	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430", "\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430", "\\u0424\\u043e\\u0442\\u043e \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
15	2025-10-15 10:45:45.364778+03	2	Разработка веб-приложений с использованием Python и фреймворка Django	2	[{"changed": {"fields": ["\\u0424\\u043e\\u0442\\u043e \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
16	2025-10-15 10:53:39.783336+03	1	Отзыв от Методистов Методист на Основы программирования на Java	1	[{"added": {}}]	25	1
17	2025-10-15 20:59:08.176115+03	1	Отзыв от Методистов Методист на Основы программирования на Java	2	[{"changed": {"fields": ["\\u041a\\u043e\\u043c\\u043c\\u0435\\u043d\\u0442\\u0430\\u0440\\u0438\\u0439 \\u043a \\u043e\\u0442\\u0437\\u044b\\u0432\\u0443"]}}]	25	1
18	2025-10-16 11:37:48.824246+03	4	уаауавлавылазщвылавщлавызщла	1	[{"added": {}}]	12	1
19	2025-10-16 11:53:46.568648+03	4	уаауавлавылазщвылавщлавызщла	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
20	2025-10-16 11:55:08.631405+03	4	уаауавлавылазщвылавщлавызщла	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
21	2025-10-16 11:55:41.467392+03	4	уаауавлавылазщвылавщлавызщла	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
22	2025-10-16 11:56:25.469949+03	4	уаауавлавылазщвылавщлавызщла	2	[{"changed": {"fields": ["\\u0424\\u043e\\u0442\\u043e \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
23	2025-10-16 12:05:25.925099+03	4	уаауавлавылазщвылавщлавызщла	2	[{"changed": {"fields": ["\\u0424\\u043e\\u0442\\u043e \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
24	2025-10-17 02:31:05.963729+03	1	Образовательная программаааааааааааааааааааааааааааааааааааааааааааааааааааааааааааааааааааа	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0442\\u0438\\u043f\\u0430 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	9	1
25	2025-10-17 02:31:20.607462+03	1	Образовательная программа	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0442\\u0438\\u043f\\u0430 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	9	1
26	2025-10-17 02:31:55.907219+03	2	Разработка веб-приложений с использованием Python и фреймворка Django	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
27	2025-10-17 02:32:32.513274+03	2	Разработка веб-приложений с использованием Python и фреймворка Django	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
28	2025-10-17 02:32:49.771828+03	1	Основы программирования на Java	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
29	2025-10-17 02:33:05.666096+03	1	Основы программирования на Java	2	[{"changed": {"fields": ["\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
30	2025-10-22 19:16:55.607684+03	2	Разработка веб-приложений с использованием Python и фреймворка Django	2	[{"changed": {"fields": ["\\u0426\\u0435\\u043d\\u0430 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
31	2025-10-22 19:17:20.705172+03	1	Основы программирования на языке Java	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
32	2025-10-22 19:17:47.015185+03	3	Квантовая физика в теории и задачах	2	[{"changed": {"fields": ["\\u0426\\u0435\\u043d\\u0430 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
33	2025-10-22 19:18:03.194865+03	2	Разработка веб-приложений с использованием Python и фреймворка Django	2	[{"changed": {"fields": ["\\u0426\\u0435\\u043d\\u0430 \\u043a\\u0443\\u0440\\u0441\\u0430"]}}]	12	1
34	2025-10-28 01:13:33.322299+03	2	Классная комната	1	[{"added": {}}]	9	1
35	2025-10-28 01:15:04.707779+03	2	Отзыв от Методистов Методист на уаауавлавылазщвылавщлавызщла	1	[{"added": {}}]	25	1
36	2025-10-28 10:50:01.561458+03	3	  - уаауавлавылазщвылавщлавызщла	3		20	1
37	2025-10-28 10:50:01.562481+03	2	  - Квантовая физика в теории и задачах	3		20	1
38	2025-10-28 10:50:01.562481+03	1	  - Основы программирования на языке Java	3		20	1
39	2025-10-28 11:00:10.120863+03	3	Курсов Слушатель	1	[{"added": {}}]	11	1
40	2025-10-28 11:20:52.566256+03	3	Курсов Слушатель	3		11	1
41	2025-10-28 11:24:18.129549+03	1	Системы Администратор	2	[{"changed": {"fields": ["First name", "Last name", "\\u0420\\u043e\\u043b\\u044c"]}}]	11	1
42	2025-10-28 14:28:34.335332+03	5	тест	1	[{"added": {}}]	10	1
43	2025-10-28 19:15:59.599385+03	1	Новая лекция	1	[{"added": {}}]	13	1
44	2025-10-28 19:24:32.172181+03	1	Новая лекция123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
49	2025-10-28 21:48:37.972109+03	1		2	lecture_name: 'Новая лекция123' -> 'Новая лекция1234'	13	1
50	2025-10-28 21:48:37.975392+03	1	Новая лекция1234	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
51	2025-10-28 21:50:01.468889+03	5	тест	3		10	1
52	2025-10-28 21:50:01.471892+03	5		3	Объект удален	10	1
53	2025-10-28 21:50:04.469078+03	6		1	id: 'None' -> '6', role_name: 'None' -> '324324'	10	1
54	2025-10-28 21:50:04.470708+03	6	324324	1	[{"added": {}}]	10	1
55	2025-10-28 21:52:49.935986+03	1		2		13	1
56	2025-10-28 21:52:49.93699+03	1	Новая лекция1234	2	[]	13	1
57	2025-10-28 21:53:01.043943+03	2		1	id: 'None' -> '2', lecture_name: 'None' -> 'тест', lecture_content: 'None' -> 'тест', lecture_document_path: 'None' -> 'путь\\путь\\ваыва.выазвыаз', lecture_order: 'None' -> '2', course: 'None' -> 'Квантовая физика в теории и задачах', is_active: 'None' -> 'True'	13	1
58	2025-10-28 21:53:01.045497+03	2	тест	1	[{"added": {}}]	13	1
59	2025-10-28 22:10:10.51432+03	3		1	id: '3', lecture_name: 'новое', lecture_content: 'новоеее', lecture_document_path: 'путь\\путь\\ваыва.выазвыаз', lecture_order: '1', course: 'Основы программирования на языке Java', is_active: 'True'	13	1
60	2025-10-28 22:10:10.515429+03	3	новое	1	[{"added": {}}]	13	1
61	2025-10-28 22:13:31.491116+03	2		2		13	1
62	2025-10-28 22:13:31.493117+03	2	тест123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
63	2025-10-28 22:16:48.384201+03	2	тест1234	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
64	2025-10-28 22:17:09.854513+03	2		2		13	1
65	2025-10-28 22:17:09.856581+03	2	тест12345	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
66	2025-10-28 22:18:32.177399+03	7		1	id: '7', role_name: '1234'	10	1
67	2025-10-28 22:18:32.17898+03	7	1234	1	[{"added": {}}]	10	1
68	2025-10-28 23:13:02.640281+03	7	1234	3		10	1
69	2025-10-28 23:13:02.641281+03	6	324324	3		10	1
70	2025-10-28 23:13:02.662284+03	6		3	Объект удален	10	1
71	2025-10-28 23:13:02.663279+03	7		3	Объект удален	10	1
72	2025-10-29 00:12:51.287982+03	8	1234	1	[{"added": {}}]	10	1
73	2025-10-29 00:13:59.622178+03	9		1	id: '9', role_name: '12345'	10	1
74	2025-10-29 00:13:59.624177+03	9	12345	1	[{"added": {}}]	10	1
75	2025-10-29 00:14:16.83418+03	8	1234	3		10	1
76	2025-10-29 00:14:16.837693+03	8		3	Объект удален	10	1
77	2025-10-29 00:19:00.778927+03	9	12345	3		10	1
78	2025-10-29 00:19:00.783936+03	9		3	Объект удален	10	1
79	2025-10-29 00:19:22.021984+03	10		1	id: '10', role_name: '213123'	10	1
80	2025-10-29 00:19:22.023452+03	10	213123	1	[{"added": {}}]	10	1
81	2025-10-29 00:20:42.42886+03	10	крутая	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
82	2025-10-29 00:22:15.835964+03	10	крутая123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
83	2025-10-29 00:22:27.774598+03	10	крутая1234	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
84	2025-10-29 00:24:46.839575+03	10	крутая1234	3		10	1
85	2025-10-29 00:24:46.842573+03	10		3	Объект удален	10	1
86	2025-10-29 00:24:57.168236+03	11		1	id: '11', role_name: '1234'	10	1
87	2025-10-29 00:24:57.16921+03	11	1234	1	[{"added": {}}]	10	1
88	2025-10-29 00:26:19.728081+03	11		2		10	1
89	2025-10-29 00:26:19.729082+03	11	1234dsfdsf	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
90	2025-10-29 00:26:40.644777+03	11		2		10	1
91	2025-10-29 00:26:40.646773+03	11	1234dsfd	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
92	2025-10-29 00:27:02.706783+03	11		2		10	1
93	2025-10-29 00:27:02.708423+03	11	1234dfdsfdsf	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
94	2025-10-29 00:27:11.880605+03	11		2		10	1
95	2025-10-29 00:27:11.882605+03	11	ваывыаыва	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
96	2025-10-29 00:27:39.115289+03	11		2		10	1
97	2025-10-29 00:27:39.117287+03	11	ваывыаыва123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
98	2025-10-29 00:29:10.134564+03	11		2		10	1
99	2025-10-29 00:29:10.13609+03	11	крутая	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
100	2025-10-29 00:30:20.625158+03	12		1	id: '12', role_name: 'новая'	10	1
101	2025-10-29 00:30:20.62652+03	12	новая	1	[{"added": {}}]	10	1
102	2025-10-29 00:30:32.526145+03	11		2		10	1
103	2025-10-29 00:30:32.527146+03	11	крутая123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
104	2025-10-29 00:30:41.372144+03	12		2		10	1
105	2025-10-29 00:30:41.373503+03	12	новая123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
106	2025-10-29 00:31:26.143122+03	11	крутая123	3		10	1
107	2025-10-29 00:31:26.143122+03	12	новая123	3		10	1
108	2025-10-29 00:31:26.149121+03	11		3	Объект удален	10	1
109	2025-10-29 00:31:26.149121+03	12		3	Объект удален	10	1
110	2025-10-29 00:31:30.451995+03	13		1	id: '13', role_name: 'прям новая'	10	1
111	2025-10-29 00:31:30.452994+03	13	прям новая	1	[{"added": {}}]	10	1
112	2025-10-29 00:32:00.122778+03	13		2		10	1
113	2025-10-29 00:32:00.123867+03	13	прям новая роль	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
114	2025-10-29 00:32:39.132335+03	13		2		10	1
175	2025-10-29 01:50:03.476484+03	1		2	last_login: '2025-10-28 08:16:13+00:00' -> '2025-10-28 22:50:03.459484+00:00'	11	1
115	2025-10-29 00:32:39.134439+03	13	прям новая рольььь	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
116	2025-10-29 00:34:11.16881+03	14		1	id: '14', role_name: 'новая'	10	1
117	2025-10-29 00:34:11.170883+03	14	новая	1	[{"added": {}}]	10	1
118	2025-10-29 00:34:40.591478+03	3		2		13	1
119	2025-10-29 00:34:40.602478+03	3	новоеее	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
120	2025-10-29 00:35:11.205293+03	3	новоеее	3		13	1
121	2025-10-29 00:35:11.210291+03	3		3	Объект удален	13	1
122	2025-10-29 00:35:50.376244+03	2		2		13	1
123	2025-10-29 00:35:50.37824+03	2	тест12345	2	[{"changed": {"fields": ["\\u0421\\u043e\\u0434\\u0435\\u0440\\u0436\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
124	2025-10-29 00:36:10.855281+03	1		1	id: '1', assignment_status_name: 'новый'	7	1
125	2025-10-29 00:36:10.856281+03	1	новый	1	[{"added": {}}]	7	1
126	2025-10-29 00:36:39.851069+03	1		2		7	1
127	2025-10-29 00:36:39.852405+03	1	новый статус	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0441\\u0442\\u0430\\u0442\\u0443\\u0441\\u0430 \\u0437\\u0430\\u0434\\u0430\\u043d\\u0438\\u044f"]}}]	7	1
128	2025-10-29 00:37:18.514307+03	1	новый статус	3		7	1
129	2025-10-29 00:37:18.517308+03	1		3	Объект удален	7	1
130	2025-10-29 00:37:27.844952+03	2		1	id: '2', assignment_status_name: 'новаяяя'	7	1
131	2025-10-29 00:37:27.845941+03	2	новаяяя	1	[{"added": {}}]	7	1
132	2025-10-29 00:37:36.609719+03	2		2		7	1
133	2025-10-29 00:37:36.610721+03	2	новая	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0441\\u0442\\u0430\\u0442\\u0443\\u0441\\u0430 \\u0437\\u0430\\u0434\\u0430\\u043d\\u0438\\u044f"]}}]	7	1
134	2025-10-29 00:44:05.459086+03	14	новая	3		10	1
135	2025-10-29 00:44:05.459086+03	13	прям новая рольььь	3		10	1
136	2025-10-29 00:44:05.465087+03	13		3	Объект удален	10	1
137	2025-10-29 00:44:05.466089+03	14		3	Объект удален	10	1
138	2025-10-29 00:44:24.895311+03	15		1	role_name: 'новая'	10	1
139	2025-10-29 00:44:24.896309+03	15	новая	1	[{"added": {}}]	10	1
140	2025-10-29 00:44:29.145733+03	15		2	role_name: 'новая' -> 'новаяяя'	10	1
141	2025-10-29 00:44:29.151737+03	15	новаяяя	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
142	2025-10-29 00:44:50.421439+03	1		2	lecture_name: 'Новая лекция1234' -> 'Новая лекция'	13	1
143	2025-10-29 00:44:50.423392+03	1	Новая лекция	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u043b\\u0435\\u043a\\u0446\\u0438\\u0438"]}}]	13	1
144	2025-10-29 00:45:08.067087+03	4		1	lecture_name: 'Новая лекция1234567', lecture_content: 'уцйуцйу', lecture_document_path: 'путь\\путь\\ваыва.йцуйцвыазвыаз', lecture_order: '3', course: 'Разработка веб-приложений с использованием Python и фреймворка Django', is_active: 'True'	13	1
145	2025-10-29 00:45:08.069085+03	4	Новая лекция1234567	1	[{"added": {}}]	13	1
146	2025-10-29 00:49:00.774849+03	16		1	role_name: 'выавыа'	10	1
147	2025-10-29 00:49:00.777421+03	16	выавыа	1	[{"added": {}}]	10	1
148	2025-10-29 00:49:14.508349+03	16		2	role_name: 'выавыа' -> 'выавыа123'	10	1
149	2025-10-29 00:49:14.510348+03	16	выавыа123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
150	2025-10-29 00:49:40.215183+03	16	выавыа123	3		10	1
151	2025-10-29 00:49:40.227115+03	16		3	Объект удален: выавыа123	10	1
152	2025-10-29 00:57:38.155191+03	17		1	role_name: 'новаяяяяяя'	10	1
153	2025-10-29 00:57:38.15719+03	17	новаяяяяяя	1	[{"added": {}}]	10	1
154	2025-10-29 00:57:45.841305+03	17		2	role_name: 'новаяяяяяя' -> 'новая'	10	1
155	2025-10-29 00:57:45.842305+03	17	новая	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
156	2025-10-29 00:57:55.985896+03	15	новаяяя	3		10	1
157	2025-10-29 00:57:55.995468+03	15		3	объект: новаяяя	10	1
158	2025-10-29 01:09:49.649261+03	18		1	role_name: 'тест'	10	1
159	2025-10-29 01:09:49.650261+03	18	тест	1	[{"added": {}}]	10	1
160	2025-10-29 01:10:00.675044+03	18		2	role_name: 'тест' -> 'тест123'	10	1
161	2025-10-29 01:10:00.676256+03	18	тест123	2	[{"changed": {"fields": ["\\u041d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0440\\u043e\\u043b\\u0438"]}}]	10	1
162	2025-10-29 01:10:10.486242+03	18	тест123	3		10	1
163	2025-10-29 01:10:10.488274+03	18		3	Объект удален: тест123	10	1
164	2025-10-29 01:24:04.567184+03	2		2	password: 'User123456!' -> 'bcrypt_sha256$$2b$12$imQP248UdHCLWJ3e9BO64uvtsf1XmYNPnxChlb8hmdxkkr5fTPVgi'	11	1
165	2025-10-29 01:24:04.571448+03	2	Методистов Методист	2	[{"changed": {"fields": ["password"]}}]	11	1
166	2025-10-29 01:24:04.583252+03	vdzki9orb80w2cxoq2ngk56e87cvvsmu		1	session_key: 'vdzki9orb80w2cxoq2ngk56e87cvvsmu', session_data: '.eJxVjDsOgzAQRO_iOrK82NhLyvScwdr1JyaJjIShinL3gESRSFPNezNv4Wlbi99aWvwUxVWAuPx2TOGZ6gHig-p9lmGu6zKxPBR50ibHOabX7XT_Dgq1sq-VIasJ93Qhg40WjMOeqXOsNKRBJwvRDn1kNIYcZoWQIaNWwbLDJD5fyIc3SA:1vDs6m:O5ru6heTVbn1x1W6vMCTmigrJqL-OA49WX-MQ4Vxtno', expire_date: '2025-11-11 22:24:04.573766+00:00'	5	1
167	2025-10-29 01:24:04.585251+03	ef9mt2ahzcgc5grkaga6h9pq63062h1l		3	Объект удален: ef9mt2ahzcgc5grkaga6h9pq63062h1l	5	1
168	2025-10-29 01:24:04.612043+03	vdzki9orb80w2cxoq2ngk56e87cvvsmu		2	expire_date: '2025-11-11 22:24:04.573766+00:00' -> '2025-11-11 22:24:04.609251+00:00'	5	1
169	2025-10-29 01:24:37.794941+03	2		2	position: 'None' -> 'старший методист цикловой методической комиссии'	11	1
170	2025-10-29 01:24:37.804075+03	2	Методистов Методист	2	[{"changed": {"fields": ["\\u041f\\u043e\\u043b\\u043d\\u043e\\u0435 \\u043d\\u0430\\u0437\\u0432\\u0430\\u043d\\u0438\\u0435 \\u0434\\u043e\\u043b\\u0436\\u043d\\u043e\\u0441\\u0442\\u0438 \\u043f\\u043e \\u043c\\u0435\\u0441\\u0442\\u0443 \\u0440\\u0430\\u0431\\u043e\\u0442\\u044b"]}}]	11	1
171	2025-10-29 01:24:56.519989+03	1		2	is_verified: 'False' -> 'True'	11	1
172	2025-10-29 01:24:56.524988+03	1	Системы Администратор	2	[{"changed": {"fields": ["\\u041f\\u043e\\u0434\\u0442\\u0432\\u0435\\u0440\\u0436\\u0434\\u0451\\u043d"]}}]	11	1
173	2025-10-29 01:49:45.818516+03	vdzki9orb80w2cxoq2ngk56e87cvvsmu		3	Объект удален: vdzki9orb80w2cxoq2ngk56e87cvvsmu	5	1
177	2025-10-29 01:50:12.83845+03	1		2	last_login: '2025-10-28 22:50:03.459484+00:00' -> '2025-10-28 22:50:12.828723+00:00'	11	1
179	2025-10-29 01:50:27.882411+03	1		2	last_login: '2025-10-28 22:50:12.828723+00:00' -> '2025-10-28 22:50:27.869715+00:00'	11	1
181	2025-10-29 01:51:06.48673+03	1		2	last_login: '2025-10-28 22:50:27.869715+00:00' -> '2025-10-28 22:51:06.474092+00:00'	11	1
183	2025-10-29 01:51:52.198791+03	1		2	last_login: '2025-10-28 22:51:06.474092+00:00' -> '2025-10-28 22:51:52.188792+00:00'	11	1
185	2025-10-29 01:51:55.360155+03	1		2	last_login: '2025-10-28 22:51:52.188792+00:00' -> '2025-10-28 22:51:55.350457+00:00'	11	1
187	2025-10-29 01:52:08.612086+03	1		2	last_login: '2025-10-28 22:51:55.350457+00:00' -> '2025-10-28 22:52:08.600087+00:00'	11	1
189	2025-10-29 01:53:42.705781+03	1		2	last_login: '2025-10-28 22:52:08.600087+00:00' -> '2025-10-28 22:53:42.689783+00:00'	11	1
191	2025-10-29 01:54:32.453443+03	1		2	last_login: '2025-10-28 22:53:42.689783+00:00' -> '2025-10-28 22:54:32.442437+00:00'	11	1
193	2025-10-29 01:54:35.619456+03	1		2	last_login: '2025-10-28 22:54:32.442437+00:00' -> '2025-10-28 22:54:35.608455+00:00'	11	1
195	2025-10-29 01:54:46.296543+03	1		2	last_login: '2025-10-28 22:54:35.608455+00:00' -> '2025-10-28 22:54:46.281540+00:00'	11	1
202	2025-10-29 02:09:07.579113+03	19	ывавыаыв	1	[{"added": {}}]	10	1
203	2025-10-29 02:09:59.120544+03	n2m9ejqe3p7ht2mekm4lxzo943dywniw		3	Объект удален: n2m9ejqe3p7ht2mekm4lxzo943dywniw	5	1
\.


--
-- TOC entry 5155 (class 0 OID 92354)
-- Dependencies: 218
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	contenttypes	contenttype
5	sessions	session
6	unireax_main	answertype
7	unireax_main	assignmentstatus
8	unireax_main	coursecategory
9	unireax_main	coursetype
10	unireax_main	role
11	unireax_main	user
12	unireax_main	course
13	unireax_main	lecture
14	unireax_main	practicalassignment
15	unireax_main	question
16	unireax_main	matchingpair
17	unireax_main	choiceoption
18	unireax_main	test
19	unireax_main	useranswer
20	unireax_main	usercourse
21	unireax_main	certificate
22	unireax_main	userpracticalassignment
23	unireax_main	feedback
24	unireax_main	courseteacher
25	unireax_main	review
26	unireax_main	testresult
27	unireax_main	usermatchinganswer
28	unireax_main	userselectedchoice
29	unireax_main	viewcourselectures
30	unireax_main	viewcoursepracticalassignments
31	unireax_main	viewcoursetests
\.


--
-- TOC entry 5153 (class 0 OID 92346)
-- Dependencies: 216
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2025-10-06 12:49:09.725784+03
2	contenttypes	0002_remove_content_type_name	2025-10-06 12:49:09.735713+03
3	auth	0001_initial	2025-10-06 12:49:09.818081+03
4	auth	0002_alter_permission_name_max_length	2025-10-06 12:49:09.823713+03
5	auth	0003_alter_user_email_max_length	2025-10-06 12:49:09.830957+03
6	auth	0004_alter_user_username_opts	2025-10-06 12:49:09.844976+03
7	auth	0005_alter_user_last_login_null	2025-10-06 12:49:09.850254+03
8	auth	0006_require_contenttypes_0002	2025-10-06 12:49:09.851987+03
9	auth	0007_alter_validators_add_error_messages	2025-10-06 12:49:09.857013+03
10	auth	0008_alter_user_username_max_length	2025-10-06 12:49:09.861666+03
11	auth	0009_alter_user_last_name_max_length	2025-10-06 12:49:09.870349+03
12	auth	0010_alter_group_name_max_length	2025-10-06 12:49:09.878938+03
13	auth	0011_update_proxy_permissions	2025-10-06 12:49:09.883563+03
14	auth	0012_alter_user_first_name_max_length	2025-10-06 12:49:09.8894+03
15	unireax_main	0001_initial	2025-10-06 12:49:10.517453+03
16	admin	0001_initial	2025-10-06 12:49:10.562137+03
17	admin	0002_logentry_remove_auto_add	2025-10-06 12:49:10.572752+03
18	admin	0003_logentry_add_action_flag_choices	2025-10-06 12:49:10.587955+03
19	sessions	0001_initial	2025-10-06 12:49:10.605213+03
20	unireax_main	0002_alter_user_role	2025-10-06 12:49:10.695366+03
21	unireax_main	0003_alter_user_educational_institution	2025-10-06 12:49:10.706799+03
22	unireax_main	0004_alter_course_course_photo_path	2025-10-06 14:14:23.2316+03
23	unireax_main	0005_user_certificat_from_the_place_of_work_path_and_more	2025-10-19 21:10:49.861+03
24	unireax_main	0006_viewcourselectures_viewcoursepracticalassignments_and_more	2025-10-27 17:42:54.332525+03
25	unireax_main	0007_db_functions_views_triggers	2025-10-27 18:27:39.814384+03
27	unireax_main	0008_course_is_active_courseteacher_is_active_and_more	2025-10-28 02:38:37.871287+03
\.


--
-- TOC entry 5214 (class 0 OID 92847)
-- Dependencies: 277
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
6qf9d1b7rg03fmiqi2ctvn9jnat0iitq	.eJxVjDsOgzAQRO_iOrK82NhLyvScwdr1JyaJjIShinL3gESRSFPNezNv4Wlbi99aWvwUxVWAuPx2TOGZ6gHig-p9lmGu6zKxPBR50ibHOabX7XT_Dgq1sq-VIasJ93Qhg40WjMOeqXOsNKRBJwvRDn1kNIYcZoWQIaNWwbLDJD5fyIc3SA:1vAXxy:40sRTZ9uYsAT3EilY1Y5Sv_UJtHDvCMGlzmN4bkfHEk	2025-11-02 21:17:14.330728+03
0tawu2g2tp191e7gyvseny9lio7wf30w	.eJxVjDsOgzAQRO_iOrK82NhLyvScwdr1JyaJjIShinL3gESRSFPNezNv4Wlbi99aWvwUxVWAuPx2TOGZ6gHig-p9lmGu6zKxPBR50ibHOabX7XT_Dgq1sq-VIasJ93Qhg40WjMOeqXOsNKRBJwvRDn1kNIYcZoWQIaNWwbLDJD5fyIc3SA:1vDspZ:RvJpuvzj4eDLLI4TZZhtYfmloaGzDPk9zxrcYCZ3G7Y	2025-11-12 02:10:21.122733+03
\.


--
-- TOC entry 5163 (class 0 OID 92408)
-- Dependencies: 226
-- Data for Name: unireax_main_answertype; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_answertype (id, answer_type_name, answer_type_description) FROM stdin;
\.


--
-- TOC entry 5165 (class 0 OID 92418)
-- Dependencies: 228
-- Data for Name: unireax_main_assignmentstatus; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_assignmentstatus (id, assignment_status_name) FROM stdin;
2	новая
\.


--
-- TOC entry 5197 (class 0 OID 92545)
-- Dependencies: 260
-- Data for Name: unireax_main_certificate; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_certificate (id, certificate_number, issue_date, certificate_file_path, user_course_id) FROM stdin;
\.


--
-- TOC entry 5189 (class 0 OID 92510)
-- Dependencies: 252
-- Data for Name: unireax_main_choiceoption; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_choiceoption (id, option_text, is_correct, question_id) FROM stdin;
\.


--
-- TOC entry 5179 (class 0 OID 92470)
-- Dependencies: 242
-- Data for Name: unireax_main_course; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_course (id, course_name, course_description, course_price, course_photo_path, has_certificate, course_max_places, course_hours, is_completed, code_room, created_by_id, course_category_id, course_type_id, is_active) FROM stdin;
3	Квантовая физика в теории и задачах	На курсе вы разберете один из интереснейших разделов физики и научитесь решать типовые задачи из раздела "Квантовая физика".	505.00	photos/physics1_K3QWMSH.png	f	30	15	f	\N	2	2	1	t
2	Разработка веб-приложений с использованием Python и фреймворка Django	Познакомьтесь с популярнейшим решением для создания веб-приложений! Вы разработаете индивидуальный проект, который станет дополнением вашего портфолио.	2298.99	photos/django.png	t	200	72	f	\N	2	1	1	t
4	уаауавлавылазщвылавщлавызщла	вповшопвщашопщшавпавпвапавпавпавпвпавпавп авпавп вапвап впвапавп вп авпвап вап ва вапвапвапвапв пва пвапвап аоывоавщыоазвыщаощвылазвщ лзывал зв щлазщывлазщылзщывл азщвыла зщвла зыщылзщы лвзыщл ащзыв лазщывлазыщвлазщвылзщщл  лазщвылащзы лщв лзщыл азвыщл аыв ы ававыаывавыаыв	1200.00	photos/angrycat_xM0xJ7s.jpg	t	\N	55	f	\N	2	1	1	t
1	Основы программирования на языке Java	Курс предназначен для студентов первых курсов технических университетов, которые хотели бы начать разбираться в языке Java на базовом уровне и улучшить свои навыки.	\N	photos/image11.png	f	\N	36	f	\N	2	1	1	t
\.


--
-- TOC entry 5167 (class 0 OID 92426)
-- Dependencies: 230
-- Data for Name: unireax_main_coursecategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_coursecategory (id, course_category_name) FROM stdin;
1	Информационные технологии
2	Физика
\.


--
-- TOC entry 5203 (class 0 OID 92573)
-- Dependencies: 266
-- Data for Name: unireax_main_courseteacher; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_courseteacher (id, start_date, course_id, teacher_id, is_active) FROM stdin;
\.


--
-- TOC entry 5169 (class 0 OID 92432)
-- Dependencies: 232
-- Data for Name: unireax_main_coursetype; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_coursetype (id, course_type_name, course_type_description) FROM stdin;
1	Образовательная программа	Курс, созданный преподавателями и методистами, преимущественно состоит из тестов.
2	Классная комната	Курс, в которой можно попасть только по специальному коду. Обычно используется преподавателями общеобразовательных и среднеспециальных учреждений для личных целей и организации своей дисциплины.
\.


--
-- TOC entry 5201 (class 0 OID 92563)
-- Dependencies: 264
-- Data for Name: unireax_main_feedback; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_feedback (id, score, is_passed, comment_feedback, user_practical_assignment_id) FROM stdin;
\.


--
-- TOC entry 5181 (class 0 OID 92478)
-- Dependencies: 244
-- Data for Name: unireax_main_lecture; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_lecture (id, lecture_name, lecture_content, lecture_document_path, lecture_order, course_id, is_active) FROM stdin;
2	тест12345	тестт	путь\\путь\\ваыва.выазвыаз	2	3	t
1	Новая лекция	Тут очень классно	путь\\путь\\ваыва.выазвыаз	1	3	t
4	Новая лекция1234567	уцйуцйу	путь\\путь\\ваыва.йцуйцвыазвыаз	3	2	t
\.


--
-- TOC entry 5187 (class 0 OID 92502)
-- Dependencies: 250
-- Data for Name: unireax_main_matchingpair; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_matchingpair (id, left_text, right_text, question_id) FROM stdin;
\.


--
-- TOC entry 5183 (class 0 OID 92486)
-- Dependencies: 246
-- Data for Name: unireax_main_practicalassignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_practicalassignment (id, practical_assignment_name, practical_assignment_description, assignment_document_path, assignment_criteria, assignment_deadline, grading_type, max_score, lecture_id, is_active) FROM stdin;
\.


--
-- TOC entry 5185 (class 0 OID 92494)
-- Dependencies: 248
-- Data for Name: unireax_main_question; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_question (id, question_text, question_score, correct_text, question_order, answer_type_id, test_id) FROM stdin;
\.


--
-- TOC entry 5205 (class 0 OID 92579)
-- Dependencies: 268
-- Data for Name: unireax_main_review; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_review (id, review_text, rating, publish_date, comment_review, course_id, user_id) FROM stdin;
1	Замечательный курс, все доходчиво объясняется в лекциях. Даже удивительно, что он бесплатный :D	5	2025-10-15 10:52:31+03	круто круто	1	2
2	крутой	4	2025-10-28 01:14:00+03	крутой	4	2
\.


--
-- TOC entry 5171 (class 0 OID 92440)
-- Dependencies: 234
-- Data for Name: unireax_main_role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_role (id, role_name) FROM stdin;
2	Администратор
3	Преподаватель
4	Слушатель курсов
1	методист
17	новая
19	ывавыаыв
\.


--
-- TOC entry 5191 (class 0 OID 92518)
-- Dependencies: 254
-- Data for Name: unireax_main_test; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_test (id, test_name, test_description, is_final, max_attempts, grading_form, passing_score, lecture_id, is_active) FROM stdin;
\.


--
-- TOC entry 5207 (class 0 OID 92587)
-- Dependencies: 270
-- Data for Name: unireax_main_testresult; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_testresult (id, completion_date, final_score, is_passed, attempt_number, test_id, user_id) FROM stdin;
\.


--
-- TOC entry 5173 (class 0 OID 92448)
-- Dependencies: 236
-- Data for Name: unireax_main_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, is_verified, profile_theme, educational_institution, role_id, certificat_from_the_place_of_work_path, "position") FROM stdin;
1	bcrypt_sha256$$2b$12$ARh5fbmKt8eftpKwDuoXFe.mv18pxpsO2HIqpDtT6FQTsL3kdc5bK	2025-10-29 02:10:21.119718+03	t	admin	Администратор	Системы	admin@ex.ru	t	t	2025-10-06 12:50:56+03	t	\N	\N	2		\N
2	bcrypt_sha256$$2b$12$imQP248UdHCLWJ3e9BO64uvtsf1XmYNPnxChlb8hmdxkkr5fTPVgi	\N	f	test_reg1	Методист	Методистов	test@mpt.ru	f	t	2025-10-06 13:11:52+03	t	common	МПТ	1		старший методист цикловой методической комиссии
\.


--
-- TOC entry 5175 (class 0 OID 92458)
-- Dependencies: 238
-- Data for Name: unireax_main_user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- TOC entry 5177 (class 0 OID 92464)
-- Dependencies: 240
-- Data for Name: unireax_main_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- TOC entry 5193 (class 0 OID 92531)
-- Dependencies: 256
-- Data for Name: unireax_main_useranswer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_useranswer (id, answer_text, answer_date, attempt_number, score, question_id, user_id) FROM stdin;
\.


--
-- TOC entry 5195 (class 0 OID 92539)
-- Dependencies: 258
-- Data for Name: unireax_main_usercourse; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_usercourse (id, registration_date, status_course, payment_date, completion_date, course_price, course_id, user_id, is_active) FROM stdin;
\.


--
-- TOC entry 5209 (class 0 OID 92593)
-- Dependencies: 272
-- Data for Name: unireax_main_usermatchinganswer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_usermatchinganswer (id, user_selected_right_text, matching_pair_id, user_answer_id) FROM stdin;
\.


--
-- TOC entry 5199 (class 0 OID 92557)
-- Dependencies: 262
-- Data for Name: unireax_main_userpracticalassignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_userpracticalassignment (id, submission_file_path, submission_date, attempt_number, practical_assignment_id, submission_status_id, user_id) FROM stdin;
\.


--
-- TOC entry 5211 (class 0 OID 92601)
-- Dependencies: 274
-- Data for Name: unireax_main_userselectedchoice; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.unireax_main_userselectedchoice (id, choice_option_id, user_answer_id) FROM stdin;
\.


--
-- TOC entry 5220 (class 0 OID 0)
-- Dependencies: 221
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- TOC entry 5221 (class 0 OID 0)
-- Dependencies: 223
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- TOC entry 5222 (class 0 OID 0)
-- Dependencies: 219
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 124, true);


--
-- TOC entry 5223 (class 0 OID 0)
-- Dependencies: 275
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 203, true);


--
-- TOC entry 5224 (class 0 OID 0)
-- Dependencies: 217
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 31, true);


--
-- TOC entry 5225 (class 0 OID 0)
-- Dependencies: 215
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 27, true);


--
-- TOC entry 5226 (class 0 OID 0)
-- Dependencies: 225
-- Name: unireax_main_answertype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_answertype_id_seq', 1, false);


--
-- TOC entry 5227 (class 0 OID 0)
-- Dependencies: 227
-- Name: unireax_main_assignmentstatus_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_assignmentstatus_id_seq', 2, true);


--
-- TOC entry 5228 (class 0 OID 0)
-- Dependencies: 259
-- Name: unireax_main_certificate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_certificate_id_seq', 1, false);


--
-- TOC entry 5229 (class 0 OID 0)
-- Dependencies: 251
-- Name: unireax_main_choiceoption_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_choiceoption_id_seq', 1, false);


--
-- TOC entry 5230 (class 0 OID 0)
-- Dependencies: 241
-- Name: unireax_main_course_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_course_id_seq', 4, true);


--
-- TOC entry 5231 (class 0 OID 0)
-- Dependencies: 229
-- Name: unireax_main_coursecategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_coursecategory_id_seq', 2, true);


--
-- TOC entry 5232 (class 0 OID 0)
-- Dependencies: 265
-- Name: unireax_main_courseteacher_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_courseteacher_id_seq', 1, false);


--
-- TOC entry 5233 (class 0 OID 0)
-- Dependencies: 231
-- Name: unireax_main_coursetype_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_coursetype_id_seq', 2, true);


--
-- TOC entry 5234 (class 0 OID 0)
-- Dependencies: 263
-- Name: unireax_main_feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_feedback_id_seq', 1, false);


--
-- TOC entry 5235 (class 0 OID 0)
-- Dependencies: 243
-- Name: unireax_main_lecture_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_lecture_id_seq', 4, true);


--
-- TOC entry 5236 (class 0 OID 0)
-- Dependencies: 249
-- Name: unireax_main_matchingpair_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_matchingpair_id_seq', 1, false);


--
-- TOC entry 5237 (class 0 OID 0)
-- Dependencies: 245
-- Name: unireax_main_practicalassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_practicalassignment_id_seq', 1, false);


--
-- TOC entry 5238 (class 0 OID 0)
-- Dependencies: 247
-- Name: unireax_main_question_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_question_id_seq', 1, false);


--
-- TOC entry 5239 (class 0 OID 0)
-- Dependencies: 267
-- Name: unireax_main_review_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_review_id_seq', 2, true);


--
-- TOC entry 5240 (class 0 OID 0)
-- Dependencies: 233
-- Name: unireax_main_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_role_id_seq', 19, true);


--
-- TOC entry 5241 (class 0 OID 0)
-- Dependencies: 253
-- Name: unireax_main_test_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_test_id_seq', 1, false);


--
-- TOC entry 5242 (class 0 OID 0)
-- Dependencies: 269
-- Name: unireax_main_testresult_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_testresult_id_seq', 1, false);


--
-- TOC entry 5243 (class 0 OID 0)
-- Dependencies: 237
-- Name: unireax_main_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_user_groups_id_seq', 1, false);


--
-- TOC entry 5244 (class 0 OID 0)
-- Dependencies: 235
-- Name: unireax_main_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_user_id_seq', 3, true);


--
-- TOC entry 5245 (class 0 OID 0)
-- Dependencies: 239
-- Name: unireax_main_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_user_user_permissions_id_seq', 1, false);


--
-- TOC entry 5246 (class 0 OID 0)
-- Dependencies: 255
-- Name: unireax_main_useranswer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_useranswer_id_seq', 1, false);


--
-- TOC entry 5247 (class 0 OID 0)
-- Dependencies: 257
-- Name: unireax_main_usercourse_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_usercourse_id_seq', 3, true);


--
-- TOC entry 5248 (class 0 OID 0)
-- Dependencies: 271
-- Name: unireax_main_usermatchinganswer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_usermatchinganswer_id_seq', 1, false);


--
-- TOC entry 5249 (class 0 OID 0)
-- Dependencies: 261
-- Name: unireax_main_userpracticalassignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_userpracticalassignment_id_seq', 1, false);


--
-- TOC entry 5250 (class 0 OID 0)
-- Dependencies: 273
-- Name: unireax_main_userselectedchoice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.unireax_main_userselectedchoice_id_seq', 1, false);


--
-- TOC entry 4826 (class 2606 OID 92405)
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- TOC entry 4831 (class 2606 OID 92391)
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- TOC entry 4834 (class 2606 OID 92380)
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4828 (class 2606 OID 92372)
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 4821 (class 2606 OID 92382)
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- TOC entry 4823 (class 2606 OID 92366)
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 4956 (class 2606 OID 92834)
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4816 (class 2606 OID 92360)
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- TOC entry 4818 (class 2606 OID 92358)
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4814 (class 2606 OID 92352)
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- TOC entry 4960 (class 2606 OID 92853)
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- TOC entry 4837 (class 2606 OID 92416)
-- Name: unireax_main_answertype unireax_main_answertype_answer_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_answertype
    ADD CONSTRAINT unireax_main_answertype_answer_type_name_key UNIQUE (answer_type_name);


--
-- TOC entry 4839 (class 2606 OID 92414)
-- Name: unireax_main_answertype unireax_main_answertype_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_answertype
    ADD CONSTRAINT unireax_main_answertype_pkey PRIMARY KEY (id);


--
-- TOC entry 4842 (class 2606 OID 92424)
-- Name: unireax_main_assignmentstatus unireax_main_assignmentstatus_assignment_status_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_assignmentstatus
    ADD CONSTRAINT unireax_main_assignmentstatus_assignment_status_name_key UNIQUE (assignment_status_name);


--
-- TOC entry 4844 (class 2606 OID 92422)
-- Name: unireax_main_assignmentstatus unireax_main_assignmentstatus_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_assignmentstatus
    ADD CONSTRAINT unireax_main_assignmentstatus_pkey PRIMARY KEY (id);


--
-- TOC entry 4910 (class 2606 OID 92553)
-- Name: unireax_main_certificate unireax_main_certificate_certificate_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_certificate
    ADD CONSTRAINT unireax_main_certificate_certificate_number_key UNIQUE (certificate_number);


--
-- TOC entry 4912 (class 2606 OID 92551)
-- Name: unireax_main_certificate unireax_main_certificate_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_certificate
    ADD CONSTRAINT unireax_main_certificate_pkey PRIMARY KEY (id);


--
-- TOC entry 4914 (class 2606 OID 92555)
-- Name: unireax_main_certificate unireax_main_certificate_user_course_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_certificate
    ADD CONSTRAINT unireax_main_certificate_user_course_id_key UNIQUE (user_course_id);


--
-- TOC entry 4891 (class 2606 OID 92516)
-- Name: unireax_main_choiceoption unireax_main_choiceoption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_choiceoption
    ADD CONSTRAINT unireax_main_choiceoption_pkey PRIMARY KEY (id);


--
-- TOC entry 4876 (class 2606 OID 92476)
-- Name: unireax_main_course unireax_main_course_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_course
    ADD CONSTRAINT unireax_main_course_pkey PRIMARY KEY (id);


--
-- TOC entry 4846 (class 2606 OID 92430)
-- Name: unireax_main_coursecategory unireax_main_coursecategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_coursecategory
    ADD CONSTRAINT unireax_main_coursecategory_pkey PRIMARY KEY (id);


--
-- TOC entry 4926 (class 2606 OID 92757)
-- Name: unireax_main_courseteacher unireax_main_courseteacher_course_id_teacher_id_2edf69b8_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_courseteacher
    ADD CONSTRAINT unireax_main_courseteacher_course_id_teacher_id_2edf69b8_uniq UNIQUE (course_id, teacher_id);


--
-- TOC entry 4928 (class 2606 OID 92577)
-- Name: unireax_main_courseteacher unireax_main_courseteacher_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_courseteacher
    ADD CONSTRAINT unireax_main_courseteacher_pkey PRIMARY KEY (id);


--
-- TOC entry 4848 (class 2606 OID 92438)
-- Name: unireax_main_coursetype unireax_main_coursetype_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_coursetype
    ADD CONSTRAINT unireax_main_coursetype_pkey PRIMARY KEY (id);


--
-- TOC entry 4921 (class 2606 OID 92569)
-- Name: unireax_main_feedback unireax_main_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_feedback
    ADD CONSTRAINT unireax_main_feedback_pkey PRIMARY KEY (id);


--
-- TOC entry 4923 (class 2606 OID 92571)
-- Name: unireax_main_feedback unireax_main_feedback_user_practical_assignment_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_feedback
    ADD CONSTRAINT unireax_main_feedback_user_practical_assignment_id_key UNIQUE (user_practical_assignment_id);


--
-- TOC entry 4879 (class 2606 OID 92484)
-- Name: unireax_main_lecture unireax_main_lecture_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_lecture
    ADD CONSTRAINT unireax_main_lecture_pkey PRIMARY KEY (id);


--
-- TOC entry 4888 (class 2606 OID 92508)
-- Name: unireax_main_matchingpair unireax_main_matchingpair_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_matchingpair
    ADD CONSTRAINT unireax_main_matchingpair_pkey PRIMARY KEY (id);


--
-- TOC entry 4882 (class 2606 OID 92492)
-- Name: unireax_main_practicalassignment unireax_main_practicalassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_practicalassignment
    ADD CONSTRAINT unireax_main_practicalassignment_pkey PRIMARY KEY (id);


--
-- TOC entry 4885 (class 2606 OID 92500)
-- Name: unireax_main_question unireax_main_question_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_question
    ADD CONSTRAINT unireax_main_question_pkey PRIMARY KEY (id);


--
-- TOC entry 4932 (class 2606 OID 92771)
-- Name: unireax_main_review unireax_main_review_course_id_user_id_f34aa2e9_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_review
    ADD CONSTRAINT unireax_main_review_course_id_user_id_f34aa2e9_uniq UNIQUE (course_id, user_id);


--
-- TOC entry 4934 (class 2606 OID 92585)
-- Name: unireax_main_review unireax_main_review_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_review
    ADD CONSTRAINT unireax_main_review_pkey PRIMARY KEY (id);


--
-- TOC entry 4850 (class 2606 OID 92444)
-- Name: unireax_main_role unireax_main_role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_role
    ADD CONSTRAINT unireax_main_role_pkey PRIMARY KEY (id);


--
-- TOC entry 4853 (class 2606 OID 92446)
-- Name: unireax_main_role unireax_main_role_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_role
    ADD CONSTRAINT unireax_main_role_role_name_key UNIQUE (role_name);


--
-- TOC entry 4895 (class 2606 OID 92524)
-- Name: unireax_main_test unireax_main_test_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_test
    ADD CONSTRAINT unireax_main_test_pkey PRIMARY KEY (id);


--
-- TOC entry 4937 (class 2606 OID 92591)
-- Name: unireax_main_testresult unireax_main_testresult_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_testresult
    ADD CONSTRAINT unireax_main_testresult_pkey PRIMARY KEY (id);


--
-- TOC entry 4941 (class 2606 OID 92785)
-- Name: unireax_main_testresult unireax_main_testresult_user_id_test_id_attempt__f168070c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_testresult
    ADD CONSTRAINT unireax_main_testresult_user_id_test_id_attempt__f168070c_uniq UNIQUE (user_id, test_id, attempt_number);


--
-- TOC entry 4862 (class 2606 OID 92462)
-- Name: unireax_main_user_groups unireax_main_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_groups
    ADD CONSTRAINT unireax_main_user_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 4865 (class 2606 OID 92617)
-- Name: unireax_main_user_groups unireax_main_user_groups_user_id_group_id_2bb24150_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_groups
    ADD CONSTRAINT unireax_main_user_groups_user_id_group_id_2bb24150_uniq UNIQUE (user_id, group_id);


--
-- TOC entry 4855 (class 2606 OID 92454)
-- Name: unireax_main_user unireax_main_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user
    ADD CONSTRAINT unireax_main_user_pkey PRIMARY KEY (id);


--
-- TOC entry 4867 (class 2606 OID 92631)
-- Name: unireax_main_user_user_permissions unireax_main_user_user_p_user_id_permission_id_ea3335a5_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_user_permissions
    ADD CONSTRAINT unireax_main_user_user_p_user_id_permission_id_ea3335a5_uniq UNIQUE (user_id, permission_id);


--
-- TOC entry 4870 (class 2606 OID 92468)
-- Name: unireax_main_user_user_permissions unireax_main_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_user_permissions
    ADD CONSTRAINT unireax_main_user_user_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4859 (class 2606 OID 92456)
-- Name: unireax_main_user unireax_main_user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user
    ADD CONSTRAINT unireax_main_user_username_key UNIQUE (username);


--
-- TOC entry 4897 (class 2606 OID 92537)
-- Name: unireax_main_useranswer unireax_main_useranswer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_useranswer
    ADD CONSTRAINT unireax_main_useranswer_pkey PRIMARY KEY (id);


--
-- TOC entry 4901 (class 2606 OID 92700)
-- Name: unireax_main_useranswer unireax_main_useranswer_user_id_question_id_atte_f1ec3827_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_useranswer
    ADD CONSTRAINT unireax_main_useranswer_user_id_question_id_atte_f1ec3827_uniq UNIQUE (user_id, question_id, attempt_number);


--
-- TOC entry 4904 (class 2606 OID 92543)
-- Name: unireax_main_usercourse unireax_main_usercourse_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usercourse
    ADD CONSTRAINT unireax_main_usercourse_pkey PRIMARY KEY (id);


--
-- TOC entry 4907 (class 2606 OID 92714)
-- Name: unireax_main_usercourse unireax_main_usercourse_user_id_course_id_8451fe70_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usercourse
    ADD CONSTRAINT unireax_main_usercourse_user_id_course_id_8451fe70_uniq UNIQUE (user_id, course_id);


--
-- TOC entry 4943 (class 2606 OID 92799)
-- Name: unireax_main_usermatchinganswer unireax_main_usermatchin_user_answer_id_matching__415f7164_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usermatchinganswer
    ADD CONSTRAINT unireax_main_usermatchin_user_answer_id_matching__415f7164_uniq UNIQUE (user_answer_id, matching_pair_id);


--
-- TOC entry 4946 (class 2606 OID 92599)
-- Name: unireax_main_usermatchinganswer unireax_main_usermatchinganswer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usermatchinganswer
    ADD CONSTRAINT unireax_main_usermatchinganswer_pkey PRIMARY KEY (id);


--
-- TOC entry 4918 (class 2606 OID 92561)
-- Name: unireax_main_userpracticalassignment unireax_main_userpracticalassignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userpracticalassignment
    ADD CONSTRAINT unireax_main_userpracticalassignment_pkey PRIMARY KEY (id);


--
-- TOC entry 4949 (class 2606 OID 92813)
-- Name: unireax_main_userselectedchoice unireax_main_userselecte_user_answer_id_choice_op_5b8b6095_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userselectedchoice
    ADD CONSTRAINT unireax_main_userselecte_user_answer_id_choice_op_5b8b6095_uniq UNIQUE (user_answer_id, choice_option_id);


--
-- TOC entry 4952 (class 2606 OID 92605)
-- Name: unireax_main_userselectedchoice unireax_main_userselectedchoice_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userselectedchoice
    ADD CONSTRAINT unireax_main_userselectedchoice_pkey PRIMARY KEY (id);


--
-- TOC entry 4824 (class 1259 OID 92406)
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- TOC entry 4829 (class 1259 OID 92402)
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- TOC entry 4832 (class 1259 OID 92403)
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- TOC entry 4819 (class 1259 OID 92388)
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- TOC entry 4954 (class 1259 OID 92845)
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- TOC entry 4957 (class 1259 OID 92846)
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- TOC entry 4958 (class 1259 OID 92855)
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- TOC entry 4961 (class 1259 OID 92854)
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- TOC entry 4835 (class 1259 OID 92606)
-- Name: unireax_main_answertype_answer_type_name_542bec1b_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_answertype_answer_type_name_542bec1b_like ON public.unireax_main_answertype USING btree (answer_type_name varchar_pattern_ops);


--
-- TOC entry 4840 (class 1259 OID 92607)
-- Name: unireax_main_assignments_assignment_status_name_aa8cfe02_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_assignments_assignment_status_name_aa8cfe02_like ON public.unireax_main_assignmentstatus USING btree (assignment_status_name varchar_pattern_ops);


--
-- TOC entry 4908 (class 1259 OID 92732)
-- Name: unireax_main_certificate_certificate_number_b6643460_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_certificate_certificate_number_b6643460_like ON public.unireax_main_certificate USING btree (certificate_number varchar_pattern_ops);


--
-- TOC entry 4892 (class 1259 OID 92691)
-- Name: unireax_main_choiceoption_question_id_7615de0b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_choiceoption_question_id_7615de0b ON public.unireax_main_choiceoption USING btree (question_id);


--
-- TOC entry 4872 (class 1259 OID 92660)
-- Name: unireax_main_course_course_category_id_6592c911; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_course_course_category_id_6592c911 ON public.unireax_main_course USING btree (course_category_id);


--
-- TOC entry 4873 (class 1259 OID 92661)
-- Name: unireax_main_course_course_type_id_62fb55a1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_course_course_type_id_62fb55a1 ON public.unireax_main_course USING btree (course_type_id);


--
-- TOC entry 4874 (class 1259 OID 92659)
-- Name: unireax_main_course_created_by_id_8e160bec; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_course_created_by_id_8e160bec ON public.unireax_main_course USING btree (created_by_id);


--
-- TOC entry 4924 (class 1259 OID 92768)
-- Name: unireax_main_courseteacher_course_id_ef1eee4d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_courseteacher_course_id_ef1eee4d ON public.unireax_main_courseteacher USING btree (course_id);


--
-- TOC entry 4929 (class 1259 OID 92769)
-- Name: unireax_main_courseteacher_teacher_id_77ead8bf; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_courseteacher_teacher_id_77ead8bf ON public.unireax_main_courseteacher USING btree (teacher_id);


--
-- TOC entry 4877 (class 1259 OID 92667)
-- Name: unireax_main_lecture_course_id_dc23a8d4; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_lecture_course_id_dc23a8d4 ON public.unireax_main_lecture USING btree (course_id);


--
-- TOC entry 4889 (class 1259 OID 92685)
-- Name: unireax_main_matchingpair_question_id_08e6ffe3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_matchingpair_question_id_08e6ffe3 ON public.unireax_main_matchingpair USING btree (question_id);


--
-- TOC entry 4880 (class 1259 OID 92673)
-- Name: unireax_main_practicalassignment_lecture_id_d1ec7e82; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_practicalassignment_lecture_id_d1ec7e82 ON public.unireax_main_practicalassignment USING btree (lecture_id);


--
-- TOC entry 4883 (class 1259 OID 92679)
-- Name: unireax_main_question_answer_type_id_ab7e6043; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_question_answer_type_id_ab7e6043 ON public.unireax_main_question USING btree (answer_type_id);


--
-- TOC entry 4886 (class 1259 OID 92698)
-- Name: unireax_main_question_test_id_db32995d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_question_test_id_db32995d ON public.unireax_main_question USING btree (test_id);


--
-- TOC entry 4930 (class 1259 OID 92782)
-- Name: unireax_main_review_course_id_e7bca48d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_review_course_id_e7bca48d ON public.unireax_main_review USING btree (course_id);


--
-- TOC entry 4935 (class 1259 OID 92783)
-- Name: unireax_main_review_user_id_d2989117; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_review_user_id_d2989117 ON public.unireax_main_review USING btree (user_id);


--
-- TOC entry 4851 (class 1259 OID 92608)
-- Name: unireax_main_role_role_name_eba78212_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_role_role_name_eba78212_like ON public.unireax_main_role USING btree (role_name varchar_pattern_ops);


--
-- TOC entry 4893 (class 1259 OID 92697)
-- Name: unireax_main_test_lecture_id_98e11ba9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_test_lecture_id_98e11ba9 ON public.unireax_main_test USING btree (lecture_id);


--
-- TOC entry 4938 (class 1259 OID 92796)
-- Name: unireax_main_testresult_test_id_40f36cc3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_testresult_test_id_40f36cc3 ON public.unireax_main_testresult USING btree (test_id);


--
-- TOC entry 4939 (class 1259 OID 92797)
-- Name: unireax_main_testresult_user_id_2e85d9ea; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_testresult_user_id_2e85d9ea ON public.unireax_main_testresult USING btree (user_id);


--
-- TOC entry 4860 (class 1259 OID 92629)
-- Name: unireax_main_user_groups_group_id_6237b61a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_user_groups_group_id_6237b61a ON public.unireax_main_user_groups USING btree (group_id);


--
-- TOC entry 4863 (class 1259 OID 92628)
-- Name: unireax_main_user_groups_user_id_fd4bf6c9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_user_groups_user_id_fd4bf6c9 ON public.unireax_main_user_groups USING btree (user_id);


--
-- TOC entry 4856 (class 1259 OID 92615)
-- Name: unireax_main_user_role_id_d2594ed5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_user_role_id_d2594ed5 ON public.unireax_main_user USING btree (role_id);


--
-- TOC entry 4868 (class 1259 OID 92643)
-- Name: unireax_main_user_user_permissions_permission_id_0320e49f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_user_user_permissions_permission_id_0320e49f ON public.unireax_main_user_user_permissions USING btree (permission_id);


--
-- TOC entry 4871 (class 1259 OID 92642)
-- Name: unireax_main_user_user_permissions_user_id_3fd48446; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_user_user_permissions_user_id_3fd48446 ON public.unireax_main_user_user_permissions USING btree (user_id);


--
-- TOC entry 4857 (class 1259 OID 92614)
-- Name: unireax_main_user_username_ab1348fb_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_user_username_ab1348fb_like ON public.unireax_main_user USING btree (username varchar_pattern_ops);


--
-- TOC entry 4898 (class 1259 OID 92711)
-- Name: unireax_main_useranswer_question_id_5efbe4c7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_useranswer_question_id_5efbe4c7 ON public.unireax_main_useranswer USING btree (question_id);


--
-- TOC entry 4899 (class 1259 OID 92712)
-- Name: unireax_main_useranswer_user_id_0583d90e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_useranswer_user_id_0583d90e ON public.unireax_main_useranswer USING btree (user_id);


--
-- TOC entry 4902 (class 1259 OID 92725)
-- Name: unireax_main_usercourse_course_id_9d4e8814; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_usercourse_course_id_9d4e8814 ON public.unireax_main_usercourse USING btree (course_id);


--
-- TOC entry 4905 (class 1259 OID 92726)
-- Name: unireax_main_usercourse_user_id_4c0e4180; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_usercourse_user_id_4c0e4180 ON public.unireax_main_usercourse USING btree (user_id);


--
-- TOC entry 4944 (class 1259 OID 92810)
-- Name: unireax_main_usermatchinganswer_matching_pair_id_831cf26d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_usermatchinganswer_matching_pair_id_831cf26d ON public.unireax_main_usermatchinganswer USING btree (matching_pair_id);


--
-- TOC entry 4947 (class 1259 OID 92811)
-- Name: unireax_main_usermatchinganswer_user_answer_id_9ca99308; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_usermatchinganswer_user_answer_id_9ca99308 ON public.unireax_main_usermatchinganswer USING btree (user_answer_id);


--
-- TOC entry 4915 (class 1259 OID 92748)
-- Name: unireax_main_userpractical_practical_assignment_id_0be1d597; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_userpractical_practical_assignment_id_0be1d597 ON public.unireax_main_userpracticalassignment USING btree (practical_assignment_id);


--
-- TOC entry 4916 (class 1259 OID 92749)
-- Name: unireax_main_userpractical_submission_status_id_f78ec5bd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_userpractical_submission_status_id_f78ec5bd ON public.unireax_main_userpracticalassignment USING btree (submission_status_id);


--
-- TOC entry 4919 (class 1259 OID 92750)
-- Name: unireax_main_userpracticalassignment_user_id_ade091af; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_userpracticalassignment_user_id_ade091af ON public.unireax_main_userpracticalassignment USING btree (user_id);


--
-- TOC entry 4950 (class 1259 OID 92824)
-- Name: unireax_main_userselectedchoice_choice_option_id_9aa937be; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_userselectedchoice_choice_option_id_9aa937be ON public.unireax_main_userselectedchoice USING btree (choice_option_id);


--
-- TOC entry 4953 (class 1259 OID 92825)
-- Name: unireax_main_userselectedchoice_user_answer_id_db6dac89; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unireax_main_userselectedchoice_user_answer_id_db6dac89 ON public.unireax_main_userselectedchoice USING btree (user_answer_id);


--
-- TOC entry 5003 (class 2620 OID 125142)
-- Name: unireax_main_feedback trigger_check_feedback; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_feedback BEFORE INSERT OR UPDATE ON public.unireax_main_feedback FOR EACH ROW EXECUTE FUNCTION public.check_feedback_score_or_passed();


--
-- TOC entry 5001 (class 2620 OID 125147)
-- Name: unireax_main_course trigger_check_methodist_role; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_methodist_role BEFORE INSERT OR UPDATE ON public.unireax_main_course FOR EACH ROW EXECUTE FUNCTION public.check_methodist_role();


--
-- TOC entry 5002 (class 2620 OID 125152)
-- Name: unireax_main_certificate trigger_check_status_course; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_status_course BEFORE INSERT ON public.unireax_main_certificate FOR EACH ROW EXECUTE FUNCTION public.check_status_course_for_certificate();


--
-- TOC entry 5004 (class 2620 OID 125145)
-- Name: unireax_main_courseteacher trigger_check_teacher_role; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_teacher_role BEFORE INSERT OR UPDATE ON public.unireax_main_courseteacher FOR EACH ROW EXECUTE FUNCTION public.check_teacher_role();


--
-- TOC entry 5005 (class 2620 OID 125150)
-- Name: unireax_main_testresult trigger_check_test_results; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_test_results BEFORE INSERT OR UPDATE ON public.unireax_main_testresult FOR EACH ROW EXECUTE FUNCTION public.check_test_results_score_or_passed();


--
-- TOC entry 4963 (class 2606 OID 92397)
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4964 (class 2606 OID 92392)
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4962 (class 2606 OID 92383)
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4999 (class 2606 OID 92835)
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5000 (class 2606 OID 92840)
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_unireax_main_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_unireax_main_user_id FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4984 (class 2606 OID 125380)
-- Name: unireax_main_certificate unireax_main_certifi_user_course_id_b6634381_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_certificate
    ADD CONSTRAINT unireax_main_certifi_user_course_id_b6634381_fk_unireax_m FOREIGN KEY (user_course_id) REFERENCES public.unireax_main_usercourse(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4978 (class 2606 OID 125375)
-- Name: unireax_main_choiceoption unireax_main_choiceo_question_id_7615de0b_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_choiceoption
    ADD CONSTRAINT unireax_main_choiceo_question_id_7615de0b_fk_unireax_m FOREIGN KEY (question_id) REFERENCES public.unireax_main_question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4970 (class 2606 OID 92649)
-- Name: unireax_main_course unireax_main_course_course_category_id_6592c911_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_course
    ADD CONSTRAINT unireax_main_course_course_category_id_6592c911_fk_unireax_m FOREIGN KEY (course_category_id) REFERENCES public.unireax_main_coursecategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4971 (class 2606 OID 92654)
-- Name: unireax_main_course unireax_main_course_course_type_id_62fb55a1_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_course
    ADD CONSTRAINT unireax_main_course_course_type_id_62fb55a1_fk_unireax_m FOREIGN KEY (course_type_id) REFERENCES public.unireax_main_coursetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4972 (class 2606 OID 92644)
-- Name: unireax_main_course unireax_main_course_created_by_id_8e160bec_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_course
    ADD CONSTRAINT unireax_main_course_created_by_id_8e160bec_fk_unireax_m FOREIGN KEY (created_by_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4989 (class 2606 OID 125370)
-- Name: unireax_main_courseteacher unireax_main_courset_course_id_ef1eee4d_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_courseteacher
    ADD CONSTRAINT unireax_main_courset_course_id_ef1eee4d_fk_unireax_m FOREIGN KEY (course_id) REFERENCES public.unireax_main_course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4990 (class 2606 OID 125365)
-- Name: unireax_main_courseteacher unireax_main_courset_teacher_id_77ead8bf_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_courseteacher
    ADD CONSTRAINT unireax_main_courset_teacher_id_77ead8bf_fk_unireax_m FOREIGN KEY (teacher_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4988 (class 2606 OID 125360)
-- Name: unireax_main_feedback unireax_main_feedbac_user_practical_assig_f7315ada_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_feedback
    ADD CONSTRAINT unireax_main_feedbac_user_practical_assig_f7315ada_fk_unireax_m FOREIGN KEY (user_practical_assignment_id) REFERENCES public.unireax_main_userpracticalassignment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4973 (class 2606 OID 125355)
-- Name: unireax_main_lecture unireax_main_lecture_course_id_dc23a8d4_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_lecture
    ADD CONSTRAINT unireax_main_lecture_course_id_dc23a8d4_fk_unireax_m FOREIGN KEY (course_id) REFERENCES public.unireax_main_course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4977 (class 2606 OID 125350)
-- Name: unireax_main_matchingpair unireax_main_matchin_question_id_08e6ffe3_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_matchingpair
    ADD CONSTRAINT unireax_main_matchin_question_id_08e6ffe3_fk_unireax_m FOREIGN KEY (question_id) REFERENCES public.unireax_main_question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4974 (class 2606 OID 92668)
-- Name: unireax_main_practicalassignment unireax_main_practic_lecture_id_d1ec7e82_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_practicalassignment
    ADD CONSTRAINT unireax_main_practic_lecture_id_d1ec7e82_fk_unireax_m FOREIGN KEY (lecture_id) REFERENCES public.unireax_main_lecture(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4975 (class 2606 OID 125345)
-- Name: unireax_main_question unireax_main_questio_answer_type_id_ab7e6043_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_question
    ADD CONSTRAINT unireax_main_questio_answer_type_id_ab7e6043_fk_unireax_m FOREIGN KEY (answer_type_id) REFERENCES public.unireax_main_answertype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4976 (class 2606 OID 125340)
-- Name: unireax_main_question unireax_main_question_test_id_db32995d_fk_unireax_main_test_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_question
    ADD CONSTRAINT unireax_main_question_test_id_db32995d_fk_unireax_main_test_id FOREIGN KEY (test_id) REFERENCES public.unireax_main_test(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4991 (class 2606 OID 125335)
-- Name: unireax_main_review unireax_main_review_course_id_e7bca48d_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_review
    ADD CONSTRAINT unireax_main_review_course_id_e7bca48d_fk_unireax_m FOREIGN KEY (course_id) REFERENCES public.unireax_main_course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4992 (class 2606 OID 125330)
-- Name: unireax_main_review unireax_main_review_user_id_d2989117_fk_unireax_main_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_review
    ADD CONSTRAINT unireax_main_review_user_id_d2989117_fk_unireax_main_user_id FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4979 (class 2606 OID 125325)
-- Name: unireax_main_test unireax_main_test_lecture_id_98e11ba9_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_test
    ADD CONSTRAINT unireax_main_test_lecture_id_98e11ba9_fk_unireax_m FOREIGN KEY (lecture_id) REFERENCES public.unireax_main_lecture(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4993 (class 2606 OID 125320)
-- Name: unireax_main_testresult unireax_main_testres_test_id_40f36cc3_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_testresult
    ADD CONSTRAINT unireax_main_testres_test_id_40f36cc3_fk_unireax_m FOREIGN KEY (test_id) REFERENCES public.unireax_main_test(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4994 (class 2606 OID 125315)
-- Name: unireax_main_testresult unireax_main_testres_user_id_2e85d9ea_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_testresult
    ADD CONSTRAINT unireax_main_testres_user_id_2e85d9ea_fk_unireax_m FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4966 (class 2606 OID 92618)
-- Name: unireax_main_user_groups unireax_main_user_gr_user_id_fd4bf6c9_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_groups
    ADD CONSTRAINT unireax_main_user_gr_user_id_fd4bf6c9_fk_unireax_m FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4967 (class 2606 OID 92623)
-- Name: unireax_main_user_groups unireax_main_user_groups_group_id_6237b61a_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_groups
    ADD CONSTRAINT unireax_main_user_groups_group_id_6237b61a_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4965 (class 2606 OID 92856)
-- Name: unireax_main_user unireax_main_user_role_id_d2594ed5_fk_unireax_main_role_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user
    ADD CONSTRAINT unireax_main_user_role_id_d2594ed5_fk_unireax_main_role_id FOREIGN KEY (role_id) REFERENCES public.unireax_main_role(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4968 (class 2606 OID 92637)
-- Name: unireax_main_user_user_permissions unireax_main_user_us_permission_id_0320e49f_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_user_permissions
    ADD CONSTRAINT unireax_main_user_us_permission_id_0320e49f_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4969 (class 2606 OID 92632)
-- Name: unireax_main_user_user_permissions unireax_main_user_us_user_id_3fd48446_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_user_user_permissions
    ADD CONSTRAINT unireax_main_user_us_user_id_3fd48446_fk_unireax_m FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4980 (class 2606 OID 125310)
-- Name: unireax_main_useranswer unireax_main_userans_question_id_5efbe4c7_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_useranswer
    ADD CONSTRAINT unireax_main_userans_question_id_5efbe4c7_fk_unireax_m FOREIGN KEY (question_id) REFERENCES public.unireax_main_question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4981 (class 2606 OID 125305)
-- Name: unireax_main_useranswer unireax_main_userans_user_id_0583d90e_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_useranswer
    ADD CONSTRAINT unireax_main_userans_user_id_0583d90e_fk_unireax_m FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4982 (class 2606 OID 125300)
-- Name: unireax_main_usercourse unireax_main_usercou_course_id_9d4e8814_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usercourse
    ADD CONSTRAINT unireax_main_usercou_course_id_9d4e8814_fk_unireax_m FOREIGN KEY (course_id) REFERENCES public.unireax_main_course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4983 (class 2606 OID 125295)
-- Name: unireax_main_usercourse unireax_main_usercou_user_id_4c0e4180_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usercourse
    ADD CONSTRAINT unireax_main_usercou_user_id_4c0e4180_fk_unireax_m FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4995 (class 2606 OID 125290)
-- Name: unireax_main_usermatchinganswer unireax_main_usermat_matching_pair_id_831cf26d_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usermatchinganswer
    ADD CONSTRAINT unireax_main_usermat_matching_pair_id_831cf26d_fk_unireax_m FOREIGN KEY (matching_pair_id) REFERENCES public.unireax_main_matchingpair(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4996 (class 2606 OID 125285)
-- Name: unireax_main_usermatchinganswer unireax_main_usermat_user_answer_id_9ca99308_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_usermatchinganswer
    ADD CONSTRAINT unireax_main_usermat_user_answer_id_9ca99308_fk_unireax_m FOREIGN KEY (user_answer_id) REFERENCES public.unireax_main_useranswer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4985 (class 2606 OID 92733)
-- Name: unireax_main_userpracticalassignment unireax_main_userpra_practical_assignment_0be1d597_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userpracticalassignment
    ADD CONSTRAINT unireax_main_userpra_practical_assignment_0be1d597_fk_unireax_m FOREIGN KEY (practical_assignment_id) REFERENCES public.unireax_main_practicalassignment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4986 (class 2606 OID 92738)
-- Name: unireax_main_userpracticalassignment unireax_main_userpra_submission_status_id_f78ec5bd_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userpracticalassignment
    ADD CONSTRAINT unireax_main_userpra_submission_status_id_f78ec5bd_fk_unireax_m FOREIGN KEY (submission_status_id) REFERENCES public.unireax_main_assignmentstatus(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4987 (class 2606 OID 125280)
-- Name: unireax_main_userpracticalassignment unireax_main_userpra_user_id_ade091af_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userpracticalassignment
    ADD CONSTRAINT unireax_main_userpra_user_id_ade091af_fk_unireax_m FOREIGN KEY (user_id) REFERENCES public.unireax_main_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4997 (class 2606 OID 125275)
-- Name: unireax_main_userselectedchoice unireax_main_usersel_choice_option_id_9aa937be_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userselectedchoice
    ADD CONSTRAINT unireax_main_usersel_choice_option_id_9aa937be_fk_unireax_m FOREIGN KEY (choice_option_id) REFERENCES public.unireax_main_choiceoption(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4998 (class 2606 OID 125270)
-- Name: unireax_main_userselectedchoice unireax_main_usersel_user_answer_id_db6dac89_fk_unireax_m; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unireax_main_userselectedchoice
    ADD CONSTRAINT unireax_main_usersel_user_answer_id_db6dac89_fk_unireax_m FOREIGN KEY (user_answer_id) REFERENCES public.unireax_main_useranswer(id) DEFERRABLE INITIALLY DEFERRED;


-- Completed on 2025-10-29 02:25:01

--
-- PostgreSQL database dump complete
--

