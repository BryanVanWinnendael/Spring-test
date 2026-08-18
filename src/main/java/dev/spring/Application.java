package dev.spring;

import dev.spring.configuration.ApplicationConfiguration;
import dev.spring.service.CourseService;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

public class Application {
    public static void main(String[] args) {
        ApplicationContext applicationContext = new AnnotationConfigApplicationContext(ApplicationConfiguration.class);
        CourseService service = applicationContext.getBean("courseService", CourseService.class);
        System.out.println(service.list());
    }
}
