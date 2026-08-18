package dev.spring.service;

import dev.spring.model.Course;
import dev.spring.repository.CourseRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class CourseService implements CrudService<Course> {
    @Autowired
    private CourseRepository repository;

    @Override
    public List<Course> list() {
        return repository.findAll();
    }

    @Override
    public Course create(Course course) {
        return null;
    }

    @Override
    public Optional<Course> get(int id) {
        return Optional.empty();
    }

    @Override
    public void update(Course course, int id) {

    }

    @Override
    public void delete(int id) {

    }
}
