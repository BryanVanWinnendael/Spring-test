package dev.spring.repository;

import dev.spring.model.Course;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;

@Repository
public class CourseRepository implements CrudRepository<Course> {
    @Override
    public List<Course> findAll() {
        List<Course> courses = new ArrayList<>();
        Course springCourse = new Course(1, "Spring", "Learn Spring", "https://www.spring.io");

        courses.add(springCourse);

        return courses;
    }
}
