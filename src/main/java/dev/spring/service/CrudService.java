package dev.spring.service;

import dev.spring.model.Course;

import java.util.List;
import java.util.Optional;

public interface CrudService<T> {
    List<T> list();
    T create(T t);
    Optional<T> get(int id);
    void update(T t, int id);
    void delete(int id);
}
