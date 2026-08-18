package dev.spring.repository;

import java.util.List;

public interface CrudRepository<T> {
    List<T> findAll();

    T createCourse(T t);
}
