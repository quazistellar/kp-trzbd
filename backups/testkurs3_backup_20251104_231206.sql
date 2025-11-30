--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3
-- Dumped by pg_dump version 16.3

-- Started on 2025-11-04 23:12:06

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
-- TOC entry 302 (class 1255 OID 147098)
-- Name: assign_teacher_to_course(integer, bigint, date); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.assign_teacher_to_course(IN p_teacher_id integer, IN p_course_id bigint, IN p_start_date date DEFAULT CURRENT_DATE)
    LANGUAGE plpgsql
    AS $$
            BEGIN
                INSERT INTO course_teacher (teacher_id, course_id, start_date)
                VALUES (p_teacher_id, p_course_id, p_start_date);
            END;
            $$;


ALTER PROCEDURE public.assign_teacher_to_course(IN p_teacher_id integer, IN p_course_id bigint, IN p_start_date date) OWNER TO postgres;

--
-- TOC entry 282 (class 1255 OID 147070)
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
                FROM lecture
                WHERE lecture.course_id = p_course_id;

                SELECT COUNT(*) INTO total_practices
                FROM practical_assignment
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id;

                SELECT COUNT(*) INTO completed_practices
                FROM user_practical_assignment
                JOIN practical_assignment ON user_practical_assignment.practical_assignment_id = practical_assignment.id
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                JOIN assignment_status ON user_practical_assignment.submission_status_id = assignment_status.id
                WHERE lecture.course_id = p_course_id
                  AND user_practical_assignment.user_id = p_user_id
                  AND assignment_status.assignment_status_name = 'completed';

                SELECT COUNT(*) INTO total_tests
                FROM test
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id;

                SELECT COUNT(*) INTO completed_tests
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

                RETURN (completed_items::DECIMAL / total_items * 100)::DECIMAL(5,2);
            END;
            $$;


ALTER FUNCTION public.calculate_course_completion(p_user_id integer, p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 281 (class 1255 OID 147069)
-- Name: calculate_course_rating(bigint); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_course_rating(p_course_id bigint) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
            BEGIN
                RETURN COALESCE(
                    (SELECT AVG(review.rating)::DECIMAL(3,2)
                     FROM review
                     WHERE review.course_id = p_course_id),
                    0.00
                );
            END;
            $$;


ALTER FUNCTION public.calculate_course_rating(p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 283 (class 1255 OID 147071)
-- Name: calculate_test_score(integer, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_test_score(p_user_id integer, p_test_id integer, p_attempt_number integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
            BEGIN
                RETURN COALESCE(
                    (SELECT SUM(user_answer.score)
                     FROM user_answer
                     JOIN question ON user_answer.question_id = question.id
                     WHERE question.test_id = p_test_id
                       AND user_answer.user_id = p_user_id
                       AND user_answer.attempt_number = p_attempt_number),
                    0
                );
            END;
            $$;


ALTER FUNCTION public.calculate_test_score(p_user_id integer, p_test_id integer, p_attempt_number integer) OWNER TO postgres;

--
-- TOC entry 299 (class 1255 OID 147093)
-- Name: calculate_total_course_points(bigint); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_total_course_points(p_course_id bigint) RETURNS integer
    LANGUAGE plpgsql
    AS $$
            DECLARE
                total_practice_points INTEGER;
                total_test_points INTEGER;
            BEGIN
                SELECT COALESCE(SUM(practical_assignment.max_score), 0) INTO total_practice_points
                FROM practical_assignment
                JOIN lecture ON practical_assignment.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id AND practical_assignment.grading_type = 'points';

                SELECT COALESCE(SUM(question.question_score), 0) INTO total_test_points
                FROM question
                JOIN test ON question.test_id = test.id
                JOIN lecture ON test.lecture_id = lecture.id
                WHERE lecture.course_id = p_course_id;

                RETURN total_practice_points + total_test_points;
            END;
            $$;


ALTER FUNCTION public.calculate_total_course_points(p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 295 (class 1255 OID 147086)
-- Name: check_feedback_score_or_passed(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_feedback_score_or_passed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                grading_type_value VARCHAR(20);
            BEGIN
                SELECT practical_assignment.grading_type INTO grading_type_value
                FROM practical_assignment
                JOIN user_practical_assignment ON practical_assignment.id = user_practical_assignment.practical_assignment_id
                WHERE user_practical_assignment.id = NEW.user_practical_assignment_id;

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
-- TOC entry 298 (class 1255 OID 147091)
-- Name: check_methodist_role(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_methodist_role() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                -- Проверяем только если created_by указан
                IF NEW.created_by_id IS NOT NULL THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM "user"
                        JOIN role ON "user".role_id = role.id
                        WHERE "user".id = NEW.created_by_id AND role.role_name = 'методист'
                    ) THEN
                        RAISE EXCEPTION 'Создателем курса может быть только пользователь с ролью "методист"';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_methodist_role() OWNER TO postgres;

--
-- TOC entry 301 (class 1255 OID 147096)
-- Name: check_status_course_for_certificate(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_status_course_for_certificate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                course_status BOOLEAN;
            BEGIN
                SELECT user_course.status_course INTO course_status
                FROM user_course WHERE user_course.id = NEW.user_course_id;

                IF NOT course_status THEN
                    RAISE EXCEPTION 'Сертификат не может быть выдан: курс не завершён для user_course_id %', NEW.user_course_id;
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_status_course_for_certificate() OWNER TO postgres;

--
-- TOC entry 297 (class 1255 OID 147089)
-- Name: check_teacher_role(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_teacher_role() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM "user"
                    JOIN role ON "user".role_id = role.id
                    WHERE "user".id = NEW.teacher_id AND role.role_name = 'преподаватель'
                ) THEN
                    RAISE EXCEPTION 'teacher_id должен быть у пользователя с ролью "преподаватель"';
                END IF;
                RETURN NEW;
            END;
            $$;


ALTER FUNCTION public.check_teacher_role() OWNER TO postgres;

--
-- TOC entry 300 (class 1255 OID 147094)
-- Name: check_test_results_score_or_passed(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_test_results_score_or_passed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
                grading_form_value VARCHAR(20);
            BEGIN
                SELECT test.grading_form INTO grading_form_value
                FROM test WHERE test.id = NEW.test_id;

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
-- TOC entry 303 (class 1255 OID 147099)
-- Name: remove_user_from_course(integer, bigint); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.remove_user_from_course(IN p_user_id integer, IN p_course_id bigint)
    LANGUAGE plpgsql
    AS $$
            BEGIN
                DELETE FROM user_course
                WHERE user_course.user_id = p_user_id AND user_course.course_id = p_course_id;
            END;
            $$;


ALTER PROCEDURE public.remove_user_from_course(IN p_user_id integer, IN p_course_id bigint) OWNER TO postgres;

--
-- TOC entry 296 (class 1255 OID 147088)
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
                    SELECT 1 FROM practical_assignment
                    JOIN lecture ON practical_assignment.lecture_id = lecture.id
                    LEFT JOIN user_practical_assignment ON practical_assignment.id = user_practical_assignment.practical_assignment_id AND user_practical_assignment.user_id = p_user_id
                    LEFT JOIN feedback ON feedback.user_practical_assignment_id = user_practical_assignment.id
                    WHERE lecture.course_id = p_course_id
                    AND (
                        (user_practical_assignment.id IS NULL) OR
                        (practical_assignment.grading_type = 'points' AND (feedback.score IS NULL OR feedback.score <= 2)) OR
                        (practical_assignment.grading_type = 'pass_fail' AND (feedback.is_passed IS NULL OR feedback.is_passed = FALSE))
                    )
                ) INTO all_practices_completed;

                SELECT NOT EXISTS(
                    SELECT 1 FROM test
                    JOIN lecture ON test.lecture_id = lecture.id
                    LEFT JOIN test_result ON test.id = test_result.test_id AND test_result.user_id = p_user_id
                    WHERE lecture.course_id = p_course_id
                    AND (
                        (test_result.id IS NULL) OR
                        (test.grading_form = 'points' AND (test_result.final_score IS NULL OR test_result.final_score < test.passing_score)) OR
                        (test.grading_form = 'pass_fail' AND (test_result.is_passed IS NULL OR test_result.is_passed = FALSE))
                    )
                ) INTO all_tests_completed;

                SELECT user_course.registration_date::TIMESTAMP INTO registration_time
                FROM user_course
                WHERE user_course.user_id = p_user_id AND user_course.course_id = p_course_id;

                IF registration_time IS NULL OR (CURRENT_TIMESTAMP - registration_time) < INTERVAL '1 hour' THEN
                    RAISE EXCEPTION 'Не прошло более часа с регистрации';
                END IF;

                IF all_practices_completed AND all_tests_completed THEN
                    UPDATE user_course SET status_course = TRUE
                    WHERE user_course.user_id = p_user_id AND user_course.course_id = p_course_id;
                ELSE
                    RAISE EXCEPTION 'Не все задания завершены';
                END IF;
            END;
            $$;


ALTER PROCEDURE public.update_course_status(IN p_user_id integer, IN p_course_id bigint) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 226 (class 1259 OID 146607)
-- Name: answer_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.answer_type (
    id bigint NOT NULL,
    answer_type_name character varying(50) NOT NULL,
    answer_type_description text
);


ALTER TABLE public.answer_type OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 146606)
-- Name: answer_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.answer_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.answer_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 228 (class 1259 OID 146617)
-- Name: assignment_status; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assignment_status (
    id bigint NOT NULL,
    assignment_status_name character varying(255) NOT NULL
);


ALTER TABLE public.assignment_status OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 146616)
-- Name: assignment_status_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.assignment_status ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.assignment_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 222 (class 1259 OID 146567)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 146566)
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
-- TOC entry 224 (class 1259 OID 146575)
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 146574)
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
-- TOC entry 220 (class 1259 OID 146561)
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
-- TOC entry 219 (class 1259 OID 146560)
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
-- TOC entry 260 (class 1259 OID 146744)
-- Name: certificate; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.certificate (
    id bigint NOT NULL,
    certificate_number character varying(255) NOT NULL,
    issue_date date NOT NULL,
    certificate_file_path character varying(255),
    user_course_id bigint NOT NULL
);


ALTER TABLE public.certificate OWNER TO postgres;

--
-- TOC entry 259 (class 1259 OID 146743)
-- Name: certificate_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.certificate ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.certificate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 252 (class 1259 OID 146709)
-- Name: choice_option; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.choice_option (
    id bigint NOT NULL,
    option_text text NOT NULL,
    is_correct boolean NOT NULL,
    question_id bigint NOT NULL
);


ALTER TABLE public.choice_option OWNER TO postgres;

--
-- TOC entry 251 (class 1259 OID 146708)
-- Name: choice_option_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.choice_option ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.choice_option_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 242 (class 1259 OID 146669)
-- Name: course; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course (
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
    created_by_id bigint,
    course_category_id bigint NOT NULL,
    course_type_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.course OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 146625)
-- Name: course_category; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_category (
    id bigint NOT NULL,
    course_category_name character varying(255) NOT NULL
);


ALTER TABLE public.course_category OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 146624)
-- Name: course_category_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.course_category ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.course_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 241 (class 1259 OID 146668)
-- Name: course_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.course ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.course_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 266 (class 1259 OID 146772)
-- Name: course_teacher; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_teacher (
    id bigint NOT NULL,
    start_date date NOT NULL,
    course_id bigint NOT NULL,
    teacher_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.course_teacher OWNER TO postgres;

--
-- TOC entry 265 (class 1259 OID 146771)
-- Name: course_teacher_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.course_teacher ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.course_teacher_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 232 (class 1259 OID 146631)
-- Name: course_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_type (
    id bigint NOT NULL,
    course_type_name character varying(255) NOT NULL,
    course_type_description text
);


ALTER TABLE public.course_type OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 146630)
-- Name: course_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.course_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.course_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 276 (class 1259 OID 147026)
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
-- TOC entry 275 (class 1259 OID 147025)
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
-- TOC entry 218 (class 1259 OID 146553)
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 146552)
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
-- TOC entry 216 (class 1259 OID 146545)
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
-- TOC entry 215 (class 1259 OID 146544)
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
-- TOC entry 277 (class 1259 OID 147046)
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO postgres;

--
-- TOC entry 264 (class 1259 OID 146762)
-- Name: feedback; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback (
    id bigint NOT NULL,
    score integer,
    is_passed boolean,
    comment_feedback text,
    user_practical_assignment_id bigint NOT NULL
);


ALTER TABLE public.feedback OWNER TO postgres;

--
-- TOC entry 263 (class 1259 OID 146761)
-- Name: feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.feedback ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 244 (class 1259 OID 146677)
-- Name: lecture; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lecture (
    id bigint NOT NULL,
    lecture_name character varying(255) NOT NULL,
    lecture_content text NOT NULL,
    lecture_document_path character varying(255),
    lecture_order integer NOT NULL,
    course_id bigint NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.lecture OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 146676)
-- Name: lecture_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.lecture ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.lecture_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 250 (class 1259 OID 146701)
-- Name: matching_pair; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.matching_pair (
    id bigint NOT NULL,
    left_text text NOT NULL,
    right_text text NOT NULL,
    question_id bigint NOT NULL
);


ALTER TABLE public.matching_pair OWNER TO postgres;

--
-- TOC entry 249 (class 1259 OID 146700)
-- Name: matching_pair_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.matching_pair ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.matching_pair_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 246 (class 1259 OID 146685)
-- Name: practical_assignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.practical_assignment (
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


ALTER TABLE public.practical_assignment OWNER TO postgres;

--
-- TOC entry 245 (class 1259 OID 146684)
-- Name: practical_assignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.practical_assignment ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.practical_assignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 248 (class 1259 OID 146693)
-- Name: question; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.question (
    id bigint NOT NULL,
    question_text text NOT NULL,
    question_score integer NOT NULL,
    correct_text text,
    question_order integer NOT NULL,
    answer_type_id bigint NOT NULL,
    test_id bigint NOT NULL
);


ALTER TABLE public.question OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 146692)
-- Name: question_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.question ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.question_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 268 (class 1259 OID 146778)
-- Name: review; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.review (
    id bigint NOT NULL,
    review_text text NOT NULL,
    rating integer NOT NULL,
    publish_date timestamp with time zone NOT NULL,
    comment_review text,
    course_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.review OWNER TO postgres;

--
-- TOC entry 267 (class 1259 OID 146777)
-- Name: review_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.review ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 234 (class 1259 OID 146639)
-- Name: role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role (
    id bigint NOT NULL,
    role_name character varying(255) NOT NULL
);


ALTER TABLE public.role OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 146638)
-- Name: role_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.role ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 254 (class 1259 OID 146717)
-- Name: test; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.test (
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


ALTER TABLE public.test OWNER TO postgres;

--
-- TOC entry 253 (class 1259 OID 146716)
-- Name: test_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.test ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.test_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 270 (class 1259 OID 146786)
-- Name: test_result; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.test_result (
    id bigint NOT NULL,
    completion_date timestamp with time zone NOT NULL,
    final_score integer,
    is_passed boolean,
    attempt_number integer NOT NULL,
    test_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.test_result OWNER TO postgres;

--
-- TOC entry 269 (class 1259 OID 146785)
-- Name: test_result_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.test_result ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.test_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 236 (class 1259 OID 146647)
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
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
    profile_theme character varying(30),
    educational_institution character varying(100),
    role_id bigint,
    certificat_from_the_place_of_work_path character varying(255),
    "position" character varying(100),
    patronymic character varying(35)
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- TOC entry 256 (class 1259 OID 146730)
-- Name: user_answer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_answer (
    id bigint NOT NULL,
    answer_text text,
    answer_date timestamp with time zone NOT NULL,
    attempt_number integer NOT NULL,
    score integer,
    question_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.user_answer OWNER TO postgres;

--
-- TOC entry 255 (class 1259 OID 146729)
-- Name: user_answer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_answer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_answer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 258 (class 1259 OID 146738)
-- Name: user_course; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_course (
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


ALTER TABLE public.user_course OWNER TO postgres;

--
-- TOC entry 257 (class 1259 OID 146737)
-- Name: user_course_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_course ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_course_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 238 (class 1259 OID 146657)
-- Name: user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_groups (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.user_groups OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 146656)
-- Name: user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 235 (class 1259 OID 146646)
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."user" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 272 (class 1259 OID 146792)
-- Name: user_matching_answer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_matching_answer (
    id bigint NOT NULL,
    user_selected_right_text text NOT NULL,
    matching_pair_id bigint NOT NULL,
    user_answer_id bigint NOT NULL
);


ALTER TABLE public.user_matching_answer OWNER TO postgres;

--
-- TOC entry 271 (class 1259 OID 146791)
-- Name: user_matching_answer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_matching_answer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_matching_answer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 262 (class 1259 OID 146756)
-- Name: user_practical_assignment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_practical_assignment (
    id bigint NOT NULL,
    submission_file_path character varying(255),
    submission_date timestamp with time zone,
    attempt_number integer NOT NULL,
    practical_assignment_id bigint NOT NULL,
    submission_status_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.user_practical_assignment OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 146755)
-- Name: user_practical_assignment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_practical_assignment ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_practical_assignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 274 (class 1259 OID 146800)
-- Name: user_selected_choice; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_selected_choice (
    id bigint NOT NULL,
    choice_option_id bigint NOT NULL,
    user_answer_id bigint NOT NULL
);


ALTER TABLE public.user_selected_choice OWNER TO postgres;

--
-- TOC entry 273 (class 1259 OID 146799)
-- Name: user_selected_choice_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_selected_choice ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_selected_choice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 240 (class 1259 OID 146663)
-- Name: user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_user_permissions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.user_user_permissions OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 146662)
-- Name: user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 279 (class 1259 OID 147077)
-- Name: view_course_lectures; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_course_lectures AS
 SELECT course.id AS course_id,
    course.course_name,
    lecture.id AS lecture_id,
    lecture.lecture_name,
    lecture.lecture_content,
    lecture.lecture_document_path,
    lecture.lecture_order
   FROM (public.course
     JOIN public.lecture ON ((lecture.course_id = course.id)));


ALTER VIEW public.view_course_lectures OWNER TO postgres;

--
-- TOC entry 278 (class 1259 OID 147072)
-- Name: view_course_practical_assignments; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_course_practical_assignments AS
 SELECT course.id AS course_id,
    course.course_name,
    lecture.id AS lecture_id,
    lecture.lecture_name,
    practical_assignment.id AS practical_assignment_id,
    practical_assignment.practical_assignment_name,
    practical_assignment.practical_assignment_description,
    practical_assignment.assignment_document_path,
    practical_assignment.assignment_criteria,
    practical_assignment.assignment_deadline,
    practical_assignment.grading_type,
    practical_assignment.max_score
   FROM ((public.course
     JOIN public.lecture ON ((lecture.course_id = course.id)))
     JOIN public.practical_assignment ON ((practical_assignment.lecture_id = lecture.id)));


ALTER VIEW public.view_course_practical_assignments OWNER TO postgres;

--
-- TOC entry 280 (class 1259 OID 147081)
-- Name: view_course_tests; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_course_tests AS
 SELECT course.id AS course_id,
    course.course_name,
    lecture.id AS lecture_id,
    lecture.lecture_name,
    test.id AS test_id,
    test.test_name,
    test.test_description,
    test.is_final,
    test.max_attempts,
    test.grading_form,
    test.passing_score,
    question.id AS question_id,
    question.question_text,
    question.answer_type_id,
    answer_type.answer_type_name,
    question.question_score,
    question.correct_text,
    question.question_order,
    choice_option.id AS choice_option_id,
    choice_option.option_text,
    choice_option.is_correct,
    matching_pair.id AS matching_pair_id,
    matching_pair.left_text,
    matching_pair.right_text
   FROM ((((((public.course
     JOIN public.lecture ON ((lecture.course_id = course.id)))
     JOIN public.test ON ((test.lecture_id = lecture.id)))
     JOIN public.question ON ((question.test_id = test.id)))
     JOIN public.answer_type ON ((question.answer_type_id = answer_type.id)))
     LEFT JOIN public.choice_option ON ((choice_option.question_id = question.id)))
     LEFT JOIN public.matching_pair ON ((matching_pair.question_id = question.id)));


ALTER VIEW public.view_course_tests OWNER TO postgres;

--
-- TOC entry 5163 (class 0 OID 146607)
-- Dependencies: 226
-- Data for Name: answer_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.answer_type (id, answer_type_name, answer_type_description) FROM stdin;
\.


--
-- TOC entry 5165 (class 0 OID 146617)
-- Dependencies: 228
-- Data for Name: assignment_status; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.assignment_status (id, assignment_status_name) FROM stdin;
\.


--
-- TOC entry 5159 (class 0 OID 146567)
-- Dependencies: 222
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- TOC entry 5161 (class 0 OID 146575)
-- Dependencies: 224
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- TOC entry 5157 (class 0 OID 146561)
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
-- TOC entry 5197 (class 0 OID 146744)
-- Dependencies: 260
-- Data for Name: certificate; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.certificate (id, certificate_number, issue_date, certificate_file_path, user_course_id) FROM stdin;
\.


--
-- TOC entry 5189 (class 0 OID 146709)
-- Dependencies: 252
-- Data for Name: choice_option; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.choice_option (id, option_text, is_correct, question_id) FROM stdin;
\.


--
-- TOC entry 5179 (class 0 OID 146669)
-- Dependencies: 242
-- Data for Name: course; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course (id, course_name, course_description, course_price, course_photo_path, has_certificate, course_max_places, course_hours, is_completed, code_room, created_by_id, course_category_id, course_type_id, is_active) FROM stdin;
1	Основы программирования на Java	Описание крутое	\N	photos/image11_t0HV0sd.png	f	\N	36	f	\N	\N	1	1	t
\.


--
-- TOC entry 5167 (class 0 OID 146625)
-- Dependencies: 230
-- Data for Name: course_category; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_category (id, course_category_name) FROM stdin;
1	Информационные технологии
2	Физика
\.


--
-- TOC entry 5203 (class 0 OID 146772)
-- Dependencies: 266
-- Data for Name: course_teacher; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_teacher (id, start_date, course_id, teacher_id, is_active) FROM stdin;
\.


--
-- TOC entry 5169 (class 0 OID 146631)
-- Dependencies: 232
-- Data for Name: course_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_type (id, course_type_name, course_type_description) FROM stdin;
1	Образовательная программа	
2	Классная комната	
\.


--
-- TOC entry 5213 (class 0 OID 147026)
-- Dependencies: 276
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
1	2025-11-04 22:54:51.781697+03	1	 	2	last_login: 'None' -> '2025-11-04 19:54:51.774680+00:00'	11	1
2	2025-11-04 22:55:19.620825+03	1	администратор	1	[Действие в админ-панели Django] role_name: 'администратор'	10	1
3	2025-11-04 22:55:19.622825+03	1	администратор	1	[{"added": {}}]	10	1
4	2025-11-04 22:55:26.586825+03	2	методист	1	[Действие в админ-панели Django] role_name: 'методист'	10	1
5	2025-11-04 22:55:26.589833+03	2	методист	1	[{"added": {}}]	10	1
6	2025-11-04 22:55:30.596267+03	3	слушатель курсов	1	[Действие в админ-панели Django] role_name: 'слушатель курсов'	10	1
7	2025-11-04 22:55:30.597839+03	3	слушатель курсов	1	[{"added": {}}]	10	1
8	2025-11-04 22:55:37.089205+03	4	преподаватель	1	[Действие в админ-панели Django] role_name: 'преподаватель'	10	1
9	2025-11-04 22:55:37.090189+03	4	преподаватель	1	[{"added": {}}]	10	1
10	2025-11-04 23:03:45.7128+03	1	Информационные технологии	1	[Действие в админ-панели Django] course_category_name: 'Информационные технологии'	8	1
11	2025-11-04 23:03:45.714781+03	1	Информационные технологии	1	[{"added": {}}]	8	1
12	2025-11-04 23:03:48.685967+03	2	Физика	1	[Действие в админ-панели Django] course_category_name: 'Физика'	8	1
13	2025-11-04 23:03:48.688947+03	2	Физика	1	[{"added": {}}]	8	1
14	2025-11-04 23:04:14.341952+03	1	Образовательная программа	1	[Действие в админ-панели Django] course_type_name: 'Образовательная программа', course_type_description: ''	9	1
15	2025-11-04 23:04:14.342951+03	1	Образовательная программа	1	[{"added": {}}]	9	1
16	2025-11-04 23:04:17.87305+03	2	Классная комната	1	[Действие в админ-панели Django] course_type_name: 'Классная комната', course_type_description: ''	9	1
17	2025-11-04 23:04:17.875046+03	2	Классная комната	1	[{"added": {}}]	9	1
18	2025-11-04 23:06:22.374114+03	1	Основы программирования на Java	1	[Действие в админ-панели Django] course_name: 'Основы программирования на Java', course_description: 'Описание крутое', course_price: 'None', course_category: 'Информационные технологии', course_photo_path: '', has_certificate: 'False', course_max_places: 'None', course_hours: '36', is_completed: 'False', code_room: 'None', course_type: 'Образовательная программа', created_by: 'None', is_active: 'True'	12	1
19	2025-11-04 23:06:22.377132+03	1	Основы программирования на Java	1	[{"added": {}}]	12	1
20	2025-11-04 23:06:40.997649+03	1	 	2	[Действие в админ-панели Django] last_login: '2025-11-04 19:54:51.774680+00:00' -> '2025-11-04 22:54:51+03:00', date_joined: '2025-11-04 19:54:10.895822+00:00' -> '2025-11-04 22:54:10+03:00', is_verified: 'False' -> 'True', role: 'None' -> 'администратор'	11	1
21	2025-11-04 23:06:41.005692+03	1	 	2	[{"changed": {"fields": ["\\u041f\\u043e\\u0434\\u0442\\u0432\\u0435\\u0440\\u0436\\u0434\\u0451\\u043d", "\\u0420\\u043e\\u043b\\u044c"]}}]	11	1
22	2025-11-04 23:11:50.983748+03	1	Основы программирования на Java	2	course_photo_path: '' -> 'photos/image11_t0HV0sd.png'	12	1
\.


--
-- TOC entry 5155 (class 0 OID 146553)
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
-- TOC entry 5153 (class 0 OID 146545)
-- Dependencies: 216
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2025-11-04 22:53:08.021805+03
2	contenttypes	0002_remove_content_type_name	2025-11-04 22:53:08.030684+03
3	auth	0001_initial	2025-11-04 22:53:08.099368+03
4	auth	0002_alter_permission_name_max_length	2025-11-04 22:53:08.105284+03
5	auth	0003_alter_user_email_max_length	2025-11-04 22:53:08.111872+03
6	auth	0004_alter_user_username_opts	2025-11-04 22:53:08.117907+03
7	auth	0005_alter_user_last_login_null	2025-11-04 22:53:08.126879+03
8	auth	0006_require_contenttypes_0002	2025-11-04 22:53:08.128874+03
9	auth	0007_alter_validators_add_error_messages	2025-11-04 22:53:08.134874+03
10	auth	0008_alter_user_username_max_length	2025-11-04 22:53:08.142875+03
11	auth	0009_alter_user_last_name_max_length	2025-11-04 22:53:08.149883+03
12	auth	0010_alter_group_name_max_length	2025-11-04 22:53:08.159875+03
13	auth	0011_update_proxy_permissions	2025-11-04 22:53:08.164873+03
14	auth	0012_alter_user_first_name_max_length	2025-11-04 22:53:08.175529+03
15	unireax_main	0001_initial	2025-11-04 22:53:08.869899+03
16	admin	0001_initial	2025-11-04 22:53:08.917496+03
17	admin	0002_logentry_remove_auto_add	2025-11-04 22:53:08.938116+03
18	admin	0003_logentry_add_action_flag_choices	2025-11-04 22:53:08.956147+03
19	sessions	0001_initial	2025-11-04 22:53:08.977607+03
20	unireax_main	0002_alter_user_role	2025-11-04 22:53:09.015321+03
21	unireax_main	0003_alter_user_educational_institution	2025-11-04 22:53:09.033474+03
22	unireax_main	0004_alter_course_course_photo_path	2025-11-04 22:53:09.072125+03
23	unireax_main	0005_user_certificat_from_the_place_of_work_path_and_more	2025-11-04 22:53:09.104296+03
24	unireax_main	0006_viewcourselectures_viewcoursepracticalassignments_and_more	2025-11-04 22:53:09.110298+03
25	unireax_main	0007_db_functions_views_triggers	2025-11-04 22:53:09.139296+03
26	unireax_main	0008_course_is_active_courseteacher_is_active_and_more	2025-11-04 22:53:09.217339+03
27	unireax_main	0009_user_patronymic_alter_user_educational_institution_and_more	2025-11-04 22:53:09.332247+03
28	unireax_main	0010_alter_user_certificat_from_the_place_of_work_path	2025-11-04 22:53:09.35425+03
29	unireax_main	0011_alter_course_created_by	2025-11-04 22:53:09.438128+03
30	unireax_main	0012_alter_user_patronymic	2025-11-04 22:53:09.453371+03
31	unireax_main	0013_alter_review_review_text_alter_answertype_table_and_more	2025-11-04 22:53:09.644741+03
\.


--
-- TOC entry 5214 (class 0 OID 147046)
-- Dependencies: 277
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
vq04879lic6y2qqhi52s87ly5dxbkcwd	.eJxVjDsOwjAQBe_iGll2vP5R0nMGa9cfHEC2FCcV4u4QKQW0b2beiwXc1hq2kZcwJ3Zmkp1-N8L4yG0H6Y7t1nnsbV1m4rvCDzr4taf8vBzu30HFUb-19ogEMllQ2QIUj2lyDpQpQIKKzRGUlpq8i6JYo7OBSSIIT2ikEYK9P9woN0A:1vGN7D:D-yzjoZ17OgP45nWbeexbcME1hm_C5TkenmFuhwVido	2025-11-18 22:54:51.786697+03
\.


--
-- TOC entry 5201 (class 0 OID 146762)
-- Dependencies: 264
-- Data for Name: feedback; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.feedback (id, score, is_passed, comment_feedback, user_practical_assignment_id) FROM stdin;
\.


--
-- TOC entry 5181 (class 0 OID 146677)
-- Dependencies: 244
-- Data for Name: lecture; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.lecture (id, lecture_name, lecture_content, lecture_document_path, lecture_order, course_id, is_active) FROM stdin;
\.


--
-- TOC entry 5187 (class 0 OID 146701)
-- Dependencies: 250
-- Data for Name: matching_pair; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.matching_pair (id, left_text, right_text, question_id) FROM stdin;
\.


--
-- TOC entry 5183 (class 0 OID 146685)
-- Dependencies: 246
-- Data for Name: practical_assignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.practical_assignment (id, practical_assignment_name, practical_assignment_description, assignment_document_path, assignment_criteria, assignment_deadline, grading_type, max_score, lecture_id, is_active) FROM stdin;
\.


--
-- TOC entry 5185 (class 0 OID 146693)
-- Dependencies: 248
-- Data for Name: question; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.question (id, question_text, question_score, correct_text, question_order, answer_type_id, test_id) FROM stdin;
\.


--
-- TOC entry 5205 (class 0 OID 146778)
-- Dependencies: 268
-- Data for Name: review; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.review (id, review_text, rating, publish_date, comment_review, course_id, user_id) FROM stdin;
\.


--
-- TOC entry 5171 (class 0 OID 146639)
-- Dependencies: 234
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.role (id, role_name) FROM stdin;
1	администратор
2	методист
3	слушатель курсов
4	преподаватель
\.


--
-- TOC entry 5191 (class 0 OID 146717)
-- Dependencies: 254
-- Data for Name: test; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.test (id, test_name, test_description, is_final, max_attempts, grading_form, passing_score, lecture_id, is_active) FROM stdin;
\.


--
-- TOC entry 5207 (class 0 OID 146786)
-- Dependencies: 270
-- Data for Name: test_result; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.test_result (id, completion_date, final_score, is_passed, attempt_number, test_id, user_id) FROM stdin;
\.


--
-- TOC entry 5173 (class 0 OID 146647)
-- Dependencies: 236
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."user" (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, is_verified, profile_theme, educational_institution, role_id, certificat_from_the_place_of_work_path, "position", patronymic) FROM stdin;
1	bcrypt_sha256$$2b$12$KCQJJxfUmlXakV1SGwuXsOSzOljr0pwfDV/caFS33maoXw99ByyxC	2025-11-04 22:54:51+03	t	admin			admin@example.com	t	t	2025-11-04 22:54:10+03	t	\N	\N	1		\N	\N
\.


--
-- TOC entry 5193 (class 0 OID 146730)
-- Dependencies: 256
-- Data for Name: user_answer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_answer (id, answer_text, answer_date, attempt_number, score, question_id, user_id) FROM stdin;
\.


--
-- TOC entry 5195 (class 0 OID 146738)
-- Dependencies: 258
-- Data for Name: user_course; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_course (id, registration_date, status_course, payment_date, completion_date, course_price, course_id, user_id, is_active) FROM stdin;
\.


--
-- TOC entry 5175 (class 0 OID 146657)
-- Dependencies: 238
-- Data for Name: user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- TOC entry 5209 (class 0 OID 146792)
-- Dependencies: 272
-- Data for Name: user_matching_answer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_matching_answer (id, user_selected_right_text, matching_pair_id, user_answer_id) FROM stdin;
\.


--
-- TOC entry 5199 (class 0 OID 146756)
-- Dependencies: 262
-- Data for Name: user_practical_assignment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_practical_assignment (id, submission_file_path, submission_date, attempt_number, practical_assignment_id, submission_status_id, user_id) FROM stdin;
\.


--
-- TOC entry 5211 (class 0 OID 146800)
-- Dependencies: 274
-- Data for Name: user_selected_choice; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_selected_choice (id, choice_option_id, user_answer_id) FROM stdin;
\.


--
-- TOC entry 5177 (class 0 OID 146663)
-- Dependencies: 240
-- Data for Name: user_user_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- TOC entry 5220 (class 0 OID 0)
-- Dependencies: 225
-- Name: answer_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.answer_type_id_seq', 1, false);


--
-- TOC entry 5221 (class 0 OID 0)
-- Dependencies: 227
-- Name: assignment_status_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.assignment_status_id_seq', 1, false);


--
-- TOC entry 5222 (class 0 OID 0)
-- Dependencies: 221
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- TOC entry 5223 (class 0 OID 0)
-- Dependencies: 223
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- TOC entry 5224 (class 0 OID 0)
-- Dependencies: 219
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 124, true);


--
-- TOC entry 5225 (class 0 OID 0)
-- Dependencies: 259
-- Name: certificate_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.certificate_id_seq', 1, false);


--
-- TOC entry 5226 (class 0 OID 0)
-- Dependencies: 251
-- Name: choice_option_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.choice_option_id_seq', 1, false);


--
-- TOC entry 5227 (class 0 OID 0)
-- Dependencies: 229
-- Name: course_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_category_id_seq', 2, true);


--
-- TOC entry 5228 (class 0 OID 0)
-- Dependencies: 241
-- Name: course_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_id_seq', 1, true);


--
-- TOC entry 5229 (class 0 OID 0)
-- Dependencies: 265
-- Name: course_teacher_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_teacher_id_seq', 1, false);


--
-- TOC entry 5230 (class 0 OID 0)
-- Dependencies: 231
-- Name: course_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_type_id_seq', 2, true);


--
-- TOC entry 5231 (class 0 OID 0)
-- Dependencies: 275
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 22, true);


--
-- TOC entry 5232 (class 0 OID 0)
-- Dependencies: 217
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 31, true);


--
-- TOC entry 5233 (class 0 OID 0)
-- Dependencies: 215
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 31, true);


--
-- TOC entry 5234 (class 0 OID 0)
-- Dependencies: 263
-- Name: feedback_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.feedback_id_seq', 1, false);


--
-- TOC entry 5235 (class 0 OID 0)
-- Dependencies: 243
-- Name: lecture_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.lecture_id_seq', 1, false);


--
-- TOC entry 5236 (class 0 OID 0)
-- Dependencies: 249
-- Name: matching_pair_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.matching_pair_id_seq', 1, false);


--
-- TOC entry 5237 (class 0 OID 0)
-- Dependencies: 245
-- Name: practical_assignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.practical_assignment_id_seq', 1, false);


--
-- TOC entry 5238 (class 0 OID 0)
-- Dependencies: 247
-- Name: question_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.question_id_seq', 1, false);


--
-- TOC entry 5239 (class 0 OID 0)
-- Dependencies: 267
-- Name: review_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.review_id_seq', 1, false);


--
-- TOC entry 5240 (class 0 OID 0)
-- Dependencies: 233
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.role_id_seq', 4, true);


--
-- TOC entry 5241 (class 0 OID 0)
-- Dependencies: 253
-- Name: test_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.test_id_seq', 1, false);


--
-- TOC entry 5242 (class 0 OID 0)
-- Dependencies: 269
-- Name: test_result_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.test_result_id_seq', 1, false);


--
-- TOC entry 5243 (class 0 OID 0)
-- Dependencies: 255
-- Name: user_answer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_answer_id_seq', 1, false);


--
-- TOC entry 5244 (class 0 OID 0)
-- Dependencies: 257
-- Name: user_course_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_course_id_seq', 1, false);


--
-- TOC entry 5245 (class 0 OID 0)
-- Dependencies: 237
-- Name: user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_groups_id_seq', 1, false);


--
-- TOC entry 5246 (class 0 OID 0)
-- Dependencies: 235
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_id_seq', 1, true);


--
-- TOC entry 5247 (class 0 OID 0)
-- Dependencies: 271
-- Name: user_matching_answer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_matching_answer_id_seq', 1, false);


--
-- TOC entry 5248 (class 0 OID 0)
-- Dependencies: 261
-- Name: user_practical_assignment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_practical_assignment_id_seq', 1, false);


--
-- TOC entry 5249 (class 0 OID 0)
-- Dependencies: 273
-- Name: user_selected_choice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_selected_choice_id_seq', 1, false);


--
-- TOC entry 5250 (class 0 OID 0)
-- Dependencies: 239
-- Name: user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_user_permissions_id_seq', 1, false);


--
-- TOC entry 4837 (class 2606 OID 146615)
-- Name: answer_type answer_type_answer_type_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answer_type
    ADD CONSTRAINT answer_type_answer_type_name_key UNIQUE (answer_type_name);


--
-- TOC entry 4839 (class 2606 OID 146613)
-- Name: answer_type answer_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answer_type
    ADD CONSTRAINT answer_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4842 (class 2606 OID 146623)
-- Name: assignment_status assignment_status_assignment_status_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assignment_status
    ADD CONSTRAINT assignment_status_assignment_status_name_key UNIQUE (assignment_status_name);


--
-- TOC entry 4844 (class 2606 OID 146621)
-- Name: assignment_status assignment_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assignment_status
    ADD CONSTRAINT assignment_status_pkey PRIMARY KEY (id);


--
-- TOC entry 4826 (class 2606 OID 146604)
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- TOC entry 4831 (class 2606 OID 146590)
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- TOC entry 4834 (class 2606 OID 146579)
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4828 (class 2606 OID 146571)
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 4821 (class 2606 OID 146581)
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- TOC entry 4823 (class 2606 OID 146565)
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 4910 (class 2606 OID 146752)
-- Name: certificate certificate_certificate_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.certificate
    ADD CONSTRAINT certificate_certificate_number_key UNIQUE (certificate_number);


--
-- TOC entry 4912 (class 2606 OID 146750)
-- Name: certificate certificate_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.certificate
    ADD CONSTRAINT certificate_pkey PRIMARY KEY (id);


--
-- TOC entry 4914 (class 2606 OID 146754)
-- Name: certificate certificate_user_course_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.certificate
    ADD CONSTRAINT certificate_user_course_id_key UNIQUE (user_course_id);


--
-- TOC entry 4891 (class 2606 OID 146715)
-- Name: choice_option choice_option_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.choice_option
    ADD CONSTRAINT choice_option_pkey PRIMARY KEY (id);


--
-- TOC entry 4846 (class 2606 OID 146629)
-- Name: course_category course_category_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_category
    ADD CONSTRAINT course_category_pkey PRIMARY KEY (id);


--
-- TOC entry 4876 (class 2606 OID 146675)
-- Name: course course_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_pkey PRIMARY KEY (id);


--
-- TOC entry 4926 (class 2606 OID 146956)
-- Name: course_teacher course_teacher_course_id_teacher_id_1a425740_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_teacher
    ADD CONSTRAINT course_teacher_course_id_teacher_id_1a425740_uniq UNIQUE (course_id, teacher_id);


--
-- TOC entry 4928 (class 2606 OID 146776)
-- Name: course_teacher course_teacher_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_teacher
    ADD CONSTRAINT course_teacher_pkey PRIMARY KEY (id);


--
-- TOC entry 4848 (class 2606 OID 146637)
-- Name: course_type course_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_type
    ADD CONSTRAINT course_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4956 (class 2606 OID 147033)
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4816 (class 2606 OID 146559)
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- TOC entry 4818 (class 2606 OID 146557)
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4814 (class 2606 OID 146551)
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- TOC entry 4960 (class 2606 OID 147052)
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- TOC entry 4921 (class 2606 OID 146768)
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (id);


--
-- TOC entry 4923 (class 2606 OID 146770)
-- Name: feedback feedback_user_practical_assignment_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_practical_assignment_id_key UNIQUE (user_practical_assignment_id);


--
-- TOC entry 4879 (class 2606 OID 146683)
-- Name: lecture lecture_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lecture
    ADD CONSTRAINT lecture_pkey PRIMARY KEY (id);


--
-- TOC entry 4888 (class 2606 OID 146707)
-- Name: matching_pair matching_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matching_pair
    ADD CONSTRAINT matching_pair_pkey PRIMARY KEY (id);


--
-- TOC entry 4882 (class 2606 OID 146691)
-- Name: practical_assignment practical_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practical_assignment
    ADD CONSTRAINT practical_assignment_pkey PRIMARY KEY (id);


--
-- TOC entry 4885 (class 2606 OID 146699)
-- Name: question question_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_pkey PRIMARY KEY (id);


--
-- TOC entry 4932 (class 2606 OID 146970)
-- Name: review review_course_id_user_id_b7c30f31_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT review_course_id_user_id_b7c30f31_uniq UNIQUE (course_id, user_id);


--
-- TOC entry 4934 (class 2606 OID 146784)
-- Name: review review_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT review_pkey PRIMARY KEY (id);


--
-- TOC entry 4850 (class 2606 OID 146643)
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- TOC entry 4853 (class 2606 OID 146645)
-- Name: role role_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_role_name_key UNIQUE (role_name);


--
-- TOC entry 4895 (class 2606 OID 146723)
-- Name: test test_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test
    ADD CONSTRAINT test_pkey PRIMARY KEY (id);


--
-- TOC entry 4937 (class 2606 OID 146790)
-- Name: test_result test_result_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_result
    ADD CONSTRAINT test_result_pkey PRIMARY KEY (id);


--
-- TOC entry 4941 (class 2606 OID 146984)
-- Name: test_result test_result_user_id_test_id_attempt_number_64d3a05c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_result
    ADD CONSTRAINT test_result_user_id_test_id_attempt_number_64d3a05c_uniq UNIQUE (user_id, test_id, attempt_number);


--
-- TOC entry 4897 (class 2606 OID 146736)
-- Name: user_answer user_answer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_answer
    ADD CONSTRAINT user_answer_pkey PRIMARY KEY (id);


--
-- TOC entry 4901 (class 2606 OID 146899)
-- Name: user_answer user_answer_user_id_question_id_attempt_number_c12aabc5_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_answer
    ADD CONSTRAINT user_answer_user_id_question_id_attempt_number_c12aabc5_uniq UNIQUE (user_id, question_id, attempt_number);


--
-- TOC entry 4904 (class 2606 OID 146742)
-- Name: user_course user_course_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course
    ADD CONSTRAINT user_course_pkey PRIMARY KEY (id);


--
-- TOC entry 4907 (class 2606 OID 146913)
-- Name: user_course user_course_user_id_course_id_0aed58f1_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course
    ADD CONSTRAINT user_course_user_id_course_id_0aed58f1_uniq UNIQUE (user_id, course_id);


--
-- TOC entry 4862 (class 2606 OID 146661)
-- Name: user_groups user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 4865 (class 2606 OID 146816)
-- Name: user_groups user_groups_user_id_group_id_40beef00_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_user_id_group_id_40beef00_uniq UNIQUE (user_id, group_id);


--
-- TOC entry 4944 (class 2606 OID 146798)
-- Name: user_matching_answer user_matching_answer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_matching_answer
    ADD CONSTRAINT user_matching_answer_pkey PRIMARY KEY (id);


--
-- TOC entry 4947 (class 2606 OID 146998)
-- Name: user_matching_answer user_matching_answer_user_answer_id_matching__724d2664_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_matching_answer
    ADD CONSTRAINT user_matching_answer_user_answer_id_matching__724d2664_uniq UNIQUE (user_answer_id, matching_pair_id);


--
-- TOC entry 4855 (class 2606 OID 146653)
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- TOC entry 4916 (class 2606 OID 146760)
-- Name: user_practical_assignment user_practical_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_practical_assignment
    ADD CONSTRAINT user_practical_assignment_pkey PRIMARY KEY (id);


--
-- TOC entry 4950 (class 2606 OID 146804)
-- Name: user_selected_choice user_selected_choice_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_selected_choice
    ADD CONSTRAINT user_selected_choice_pkey PRIMARY KEY (id);


--
-- TOC entry 4953 (class 2606 OID 147012)
-- Name: user_selected_choice user_selected_choice_user_answer_id_choice_op_09302079_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_selected_choice
    ADD CONSTRAINT user_selected_choice_user_answer_id_choice_op_09302079_uniq UNIQUE (user_answer_id, choice_option_id);


--
-- TOC entry 4868 (class 2606 OID 146667)
-- Name: user_user_permissions user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_user_permissions
    ADD CONSTRAINT user_user_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4871 (class 2606 OID 146830)
-- Name: user_user_permissions user_user_permissions_user_id_permission_id_7dc6e2e0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_user_permissions
    ADD CONSTRAINT user_user_permissions_user_id_permission_id_7dc6e2e0_uniq UNIQUE (user_id, permission_id);


--
-- TOC entry 4859 (class 2606 OID 146655)
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- TOC entry 4835 (class 1259 OID 146805)
-- Name: answer_type_answer_type_name_173fbdfb_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX answer_type_answer_type_name_173fbdfb_like ON public.answer_type USING btree (answer_type_name varchar_pattern_ops);


--
-- TOC entry 4840 (class 1259 OID 146806)
-- Name: assignment_status_assignment_status_name_3ce650fd_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX assignment_status_assignment_status_name_3ce650fd_like ON public.assignment_status USING btree (assignment_status_name varchar_pattern_ops);


--
-- TOC entry 4824 (class 1259 OID 146605)
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- TOC entry 4829 (class 1259 OID 146601)
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- TOC entry 4832 (class 1259 OID 146602)
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- TOC entry 4819 (class 1259 OID 146587)
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- TOC entry 4908 (class 1259 OID 146931)
-- Name: certificate_certificate_number_8a9605fc_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX certificate_certificate_number_8a9605fc_like ON public.certificate USING btree (certificate_number varchar_pattern_ops);


--
-- TOC entry 4892 (class 1259 OID 146890)
-- Name: choice_option_question_id_591bffeb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX choice_option_question_id_591bffeb ON public.choice_option USING btree (question_id);


--
-- TOC entry 4872 (class 1259 OID 146859)
-- Name: course_course_category_id_4356d303; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX course_course_category_id_4356d303 ON public.course USING btree (course_category_id);


--
-- TOC entry 4873 (class 1259 OID 146860)
-- Name: course_course_type_id_394a09df; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX course_course_type_id_394a09df ON public.course USING btree (course_type_id);


--
-- TOC entry 4874 (class 1259 OID 146858)
-- Name: course_created_by_id_35db9350; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX course_created_by_id_35db9350 ON public.course USING btree (created_by_id);


--
-- TOC entry 4924 (class 1259 OID 146967)
-- Name: course_teacher_course_id_1b7990cd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX course_teacher_course_id_1b7990cd ON public.course_teacher USING btree (course_id);


--
-- TOC entry 4929 (class 1259 OID 146968)
-- Name: course_teacher_teacher_id_eb2a1071; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX course_teacher_teacher_id_eb2a1071 ON public.course_teacher USING btree (teacher_id);


--
-- TOC entry 4954 (class 1259 OID 147044)
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- TOC entry 4957 (class 1259 OID 147045)
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- TOC entry 4958 (class 1259 OID 147054)
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- TOC entry 4961 (class 1259 OID 147053)
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- TOC entry 4877 (class 1259 OID 146866)
-- Name: lecture_course_id_70e938b2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lecture_course_id_70e938b2 ON public.lecture USING btree (course_id);


--
-- TOC entry 4889 (class 1259 OID 146884)
-- Name: matching_pair_question_id_b626f4fa; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX matching_pair_question_id_b626f4fa ON public.matching_pair USING btree (question_id);


--
-- TOC entry 4880 (class 1259 OID 146872)
-- Name: practical_assignment_lecture_id_b866701b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX practical_assignment_lecture_id_b866701b ON public.practical_assignment USING btree (lecture_id);


--
-- TOC entry 4883 (class 1259 OID 146878)
-- Name: question_answer_type_id_9111b471; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX question_answer_type_id_9111b471 ON public.question USING btree (answer_type_id);


--
-- TOC entry 4886 (class 1259 OID 146897)
-- Name: question_test_id_6c277152; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX question_test_id_6c277152 ON public.question USING btree (test_id);


--
-- TOC entry 4930 (class 1259 OID 146981)
-- Name: review_course_id_0a31fb86; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX review_course_id_0a31fb86 ON public.review USING btree (course_id);


--
-- TOC entry 4935 (class 1259 OID 146982)
-- Name: review_user_id_1520d914; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX review_user_id_1520d914 ON public.review USING btree (user_id);


--
-- TOC entry 4851 (class 1259 OID 146807)
-- Name: role_role_name_d4cf81e5_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX role_role_name_d4cf81e5_like ON public.role USING btree (role_name varchar_pattern_ops);


--
-- TOC entry 4893 (class 1259 OID 146896)
-- Name: test_lecture_id_31ebf79a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX test_lecture_id_31ebf79a ON public.test USING btree (lecture_id);


--
-- TOC entry 4938 (class 1259 OID 146995)
-- Name: test_result_test_id_de0c0a88; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX test_result_test_id_de0c0a88 ON public.test_result USING btree (test_id);


--
-- TOC entry 4939 (class 1259 OID 146996)
-- Name: test_result_user_id_42e76a6b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX test_result_user_id_42e76a6b ON public.test_result USING btree (user_id);


--
-- TOC entry 4898 (class 1259 OID 146910)
-- Name: user_answer_question_id_62eab67d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_answer_question_id_62eab67d ON public.user_answer USING btree (question_id);


--
-- TOC entry 4899 (class 1259 OID 146911)
-- Name: user_answer_user_id_c5d32cc6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_answer_user_id_c5d32cc6 ON public.user_answer USING btree (user_id);


--
-- TOC entry 4902 (class 1259 OID 146924)
-- Name: user_course_course_id_01715d98; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_course_course_id_01715d98 ON public.user_course USING btree (course_id);


--
-- TOC entry 4905 (class 1259 OID 146925)
-- Name: user_course_user_id_496a571e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_course_user_id_496a571e ON public.user_course USING btree (user_id);


--
-- TOC entry 4860 (class 1259 OID 146828)
-- Name: user_groups_group_id_b76f8aba; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_groups_group_id_b76f8aba ON public.user_groups USING btree (group_id);


--
-- TOC entry 4863 (class 1259 OID 146827)
-- Name: user_groups_user_id_abaea130; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_groups_user_id_abaea130 ON public.user_groups USING btree (user_id);


--
-- TOC entry 4942 (class 1259 OID 147009)
-- Name: user_matching_answer_matching_pair_id_c1596c76; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_matching_answer_matching_pair_id_c1596c76 ON public.user_matching_answer USING btree (matching_pair_id);


--
-- TOC entry 4945 (class 1259 OID 147010)
-- Name: user_matching_answer_user_answer_id_d6d41324; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_matching_answer_user_answer_id_d6d41324 ON public.user_matching_answer USING btree (user_answer_id);


--
-- TOC entry 4917 (class 1259 OID 146947)
-- Name: user_practical_assignment_practical_assignment_id_5ed6e43d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_practical_assignment_practical_assignment_id_5ed6e43d ON public.user_practical_assignment USING btree (practical_assignment_id);


--
-- TOC entry 4918 (class 1259 OID 146948)
-- Name: user_practical_assignment_submission_status_id_db7a08be; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_practical_assignment_submission_status_id_db7a08be ON public.user_practical_assignment USING btree (submission_status_id);


--
-- TOC entry 4919 (class 1259 OID 146949)
-- Name: user_practical_assignment_user_id_ebf31370; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_practical_assignment_user_id_ebf31370 ON public.user_practical_assignment USING btree (user_id);


--
-- TOC entry 4856 (class 1259 OID 146814)
-- Name: user_role_id_c3a87a3d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_role_id_c3a87a3d ON public."user" USING btree (role_id);


--
-- TOC entry 4948 (class 1259 OID 147023)
-- Name: user_selected_choice_choice_option_id_a2738e8a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_selected_choice_choice_option_id_a2738e8a ON public.user_selected_choice USING btree (choice_option_id);


--
-- TOC entry 4951 (class 1259 OID 147024)
-- Name: user_selected_choice_user_answer_id_1f8ac803; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_selected_choice_user_answer_id_1f8ac803 ON public.user_selected_choice USING btree (user_answer_id);


--
-- TOC entry 4866 (class 1259 OID 146842)
-- Name: user_user_permissions_permission_id_9deb68a3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_user_permissions_permission_id_9deb68a3 ON public.user_user_permissions USING btree (permission_id);


--
-- TOC entry 4869 (class 1259 OID 146841)
-- Name: user_user_permissions_user_id_ed4a47ea; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_user_permissions_user_id_ed4a47ea ON public.user_user_permissions USING btree (user_id);


--
-- TOC entry 4857 (class 1259 OID 146813)
-- Name: user_username_cf016618_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_username_cf016618_like ON public."user" USING btree (username varchar_pattern_ops);


--
-- TOC entry 5003 (class 2620 OID 147087)
-- Name: feedback trigger_check_feedback; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_feedback BEFORE INSERT OR UPDATE ON public.feedback FOR EACH ROW EXECUTE FUNCTION public.check_feedback_score_or_passed();


--
-- TOC entry 5001 (class 2620 OID 147092)
-- Name: course trigger_check_methodist_role; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_methodist_role BEFORE INSERT OR UPDATE ON public.course FOR EACH ROW EXECUTE FUNCTION public.check_methodist_role();


--
-- TOC entry 5002 (class 2620 OID 147097)
-- Name: certificate trigger_check_status_course; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_status_course BEFORE INSERT ON public.certificate FOR EACH ROW EXECUTE FUNCTION public.check_status_course_for_certificate();


--
-- TOC entry 5004 (class 2620 OID 147090)
-- Name: course_teacher trigger_check_teacher_role; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_teacher_role BEFORE INSERT OR UPDATE ON public.course_teacher FOR EACH ROW EXECUTE FUNCTION public.check_teacher_role();


--
-- TOC entry 5005 (class 2620 OID 147095)
-- Name: test_result trigger_check_test_results; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_check_test_results BEFORE INSERT OR UPDATE ON public.test_result FOR EACH ROW EXECUTE FUNCTION public.check_test_results_score_or_passed();


--
-- TOC entry 4963 (class 2606 OID 146596)
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4964 (class 2606 OID 146591)
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4962 (class 2606 OID 146582)
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4984 (class 2606 OID 146926)
-- Name: certificate certificate_user_course_id_e50c5039_fk_user_course_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.certificate
    ADD CONSTRAINT certificate_user_course_id_e50c5039_fk_user_course_id FOREIGN KEY (user_course_id) REFERENCES public.user_course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4978 (class 2606 OID 146885)
-- Name: choice_option choice_option_question_id_591bffeb_fk_question_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.choice_option
    ADD CONSTRAINT choice_option_question_id_591bffeb_fk_question_id FOREIGN KEY (question_id) REFERENCES public.question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4970 (class 2606 OID 146848)
-- Name: course course_course_category_id_4356d303_fk_course_category_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_course_category_id_4356d303_fk_course_category_id FOREIGN KEY (course_category_id) REFERENCES public.course_category(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4971 (class 2606 OID 146853)
-- Name: course course_course_type_id_394a09df_fk_course_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_course_type_id_394a09df_fk_course_type_id FOREIGN KEY (course_type_id) REFERENCES public.course_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4972 (class 2606 OID 147134)
-- Name: course course_created_by_id_35db9350_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_created_by_id_35db9350_fk_user_id FOREIGN KEY (created_by_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4989 (class 2606 OID 146957)
-- Name: course_teacher course_teacher_course_id_1b7990cd_fk_course_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_teacher
    ADD CONSTRAINT course_teacher_course_id_1b7990cd_fk_course_id FOREIGN KEY (course_id) REFERENCES public.course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4990 (class 2606 OID 146962)
-- Name: course_teacher course_teacher_teacher_id_eb2a1071_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_teacher
    ADD CONSTRAINT course_teacher_teacher_id_eb2a1071_fk_user_id FOREIGN KEY (teacher_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4999 (class 2606 OID 147034)
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 5000 (class 2606 OID 147039)
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4988 (class 2606 OID 146950)
-- Name: feedback feedback_user_practical_assig_ebb447a3_fk_user_prac; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_user_practical_assig_ebb447a3_fk_user_prac FOREIGN KEY (user_practical_assignment_id) REFERENCES public.user_practical_assignment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4973 (class 2606 OID 146861)
-- Name: lecture lecture_course_id_70e938b2_fk_course_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lecture
    ADD CONSTRAINT lecture_course_id_70e938b2_fk_course_id FOREIGN KEY (course_id) REFERENCES public.course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4977 (class 2606 OID 146879)
-- Name: matching_pair matching_pair_question_id_b626f4fa_fk_question_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matching_pair
    ADD CONSTRAINT matching_pair_question_id_b626f4fa_fk_question_id FOREIGN KEY (question_id) REFERENCES public.question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4974 (class 2606 OID 146867)
-- Name: practical_assignment practical_assignment_lecture_id_b866701b_fk_lecture_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.practical_assignment
    ADD CONSTRAINT practical_assignment_lecture_id_b866701b_fk_lecture_id FOREIGN KEY (lecture_id) REFERENCES public.lecture(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4975 (class 2606 OID 146873)
-- Name: question question_answer_type_id_9111b471_fk_answer_type_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_answer_type_id_9111b471_fk_answer_type_id FOREIGN KEY (answer_type_id) REFERENCES public.answer_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4976 (class 2606 OID 146724)
-- Name: question question_test_id_6c277152_fk_test_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_test_id_6c277152_fk_test_id FOREIGN KEY (test_id) REFERENCES public.test(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4991 (class 2606 OID 146971)
-- Name: review review_course_id_0a31fb86_fk_course_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT review_course_id_0a31fb86_fk_course_id FOREIGN KEY (course_id) REFERENCES public.course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4992 (class 2606 OID 146976)
-- Name: review review_user_id_1520d914_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.review
    ADD CONSTRAINT review_user_id_1520d914_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4979 (class 2606 OID 146891)
-- Name: test test_lecture_id_31ebf79a_fk_lecture_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test
    ADD CONSTRAINT test_lecture_id_31ebf79a_fk_lecture_id FOREIGN KEY (lecture_id) REFERENCES public.lecture(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4993 (class 2606 OID 146985)
-- Name: test_result test_result_test_id_de0c0a88_fk_test_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_result
    ADD CONSTRAINT test_result_test_id_de0c0a88_fk_test_id FOREIGN KEY (test_id) REFERENCES public.test(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4994 (class 2606 OID 146990)
-- Name: test_result test_result_user_id_42e76a6b_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_result
    ADD CONSTRAINT test_result_user_id_42e76a6b_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4980 (class 2606 OID 146900)
-- Name: user_answer user_answer_question_id_62eab67d_fk_question_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_answer
    ADD CONSTRAINT user_answer_question_id_62eab67d_fk_question_id FOREIGN KEY (question_id) REFERENCES public.question(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4981 (class 2606 OID 146905)
-- Name: user_answer user_answer_user_id_c5d32cc6_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_answer
    ADD CONSTRAINT user_answer_user_id_c5d32cc6_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4982 (class 2606 OID 146914)
-- Name: user_course user_course_course_id_01715d98_fk_course_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course
    ADD CONSTRAINT user_course_course_id_01715d98_fk_course_id FOREIGN KEY (course_id) REFERENCES public.course(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4983 (class 2606 OID 146919)
-- Name: user_course user_course_user_id_496a571e_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course
    ADD CONSTRAINT user_course_user_id_496a571e_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4966 (class 2606 OID 146822)
-- Name: user_groups user_groups_group_id_b76f8aba_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_group_id_b76f8aba_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4967 (class 2606 OID 146817)
-- Name: user_groups user_groups_user_id_abaea130_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_groups
    ADD CONSTRAINT user_groups_user_id_abaea130_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4995 (class 2606 OID 146999)
-- Name: user_matching_answer user_matching_answer_matching_pair_id_c1596c76_fk_matching_; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_matching_answer
    ADD CONSTRAINT user_matching_answer_matching_pair_id_c1596c76_fk_matching_ FOREIGN KEY (matching_pair_id) REFERENCES public.matching_pair(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4996 (class 2606 OID 147004)
-- Name: user_matching_answer user_matching_answer_user_answer_id_d6d41324_fk_user_answer_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_matching_answer
    ADD CONSTRAINT user_matching_answer_user_answer_id_d6d41324_fk_user_answer_id FOREIGN KEY (user_answer_id) REFERENCES public.user_answer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4985 (class 2606 OID 146932)
-- Name: user_practical_assignment user_practical_assig_practical_assignment_5ed6e43d_fk_practical; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_practical_assignment
    ADD CONSTRAINT user_practical_assig_practical_assignment_5ed6e43d_fk_practical FOREIGN KEY (practical_assignment_id) REFERENCES public.practical_assignment(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4986 (class 2606 OID 146937)
-- Name: user_practical_assignment user_practical_assig_submission_status_id_db7a08be_fk_assignmen; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_practical_assignment
    ADD CONSTRAINT user_practical_assig_submission_status_id_db7a08be_fk_assignmen FOREIGN KEY (submission_status_id) REFERENCES public.assignment_status(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4987 (class 2606 OID 146942)
-- Name: user_practical_assignment user_practical_assignment_user_id_ebf31370_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_practical_assignment
    ADD CONSTRAINT user_practical_assignment_user_id_ebf31370_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4965 (class 2606 OID 147055)
-- Name: user user_role_id_c3a87a3d_fk_role_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_role_id_c3a87a3d_fk_role_id FOREIGN KEY (role_id) REFERENCES public.role(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4997 (class 2606 OID 147013)
-- Name: user_selected_choice user_selected_choice_choice_option_id_a2738e8a_fk_choice_op; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_selected_choice
    ADD CONSTRAINT user_selected_choice_choice_option_id_a2738e8a_fk_choice_op FOREIGN KEY (choice_option_id) REFERENCES public.choice_option(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4998 (class 2606 OID 147018)
-- Name: user_selected_choice user_selected_choice_user_answer_id_1f8ac803_fk_user_answer_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_selected_choice
    ADD CONSTRAINT user_selected_choice_user_answer_id_1f8ac803_fk_user_answer_id FOREIGN KEY (user_answer_id) REFERENCES public.user_answer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4968 (class 2606 OID 146836)
-- Name: user_user_permissions user_user_permission_permission_id_9deb68a3_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_user_permissions
    ADD CONSTRAINT user_user_permission_permission_id_9deb68a3_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4969 (class 2606 OID 146831)
-- Name: user_user_permissions user_user_permissions_user_id_ed4a47ea_fk_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_user_permissions
    ADD CONSTRAINT user_user_permissions_user_id_ed4a47ea_fk_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) DEFERRABLE INITIALLY DEFERRED;


-- Completed on 2025-11-04 23:12:06

--
-- PostgreSQL database dump complete
--

