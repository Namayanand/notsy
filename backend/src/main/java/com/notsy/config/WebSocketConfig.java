package com.notsy.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import org.springframework.web.socket.server.standard.ServletServerContainerFactoryBean;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final StreamingHandler streamingHandler;

    public WebSocketConfig(StreamingHandler streamingHandler) {
        this.streamingHandler = streamingHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(streamingHandler, "/ws/stream")
            .setAllowedOrigins("*");
    }

    @Bean
    public ServletServerContainerFactoryBean servletServerContainerFactoryBean() {
        ServletServerContainerFactoryBean bean = new ServletServerContainerFactoryBean();
        bean.setMaxTextMessageBufferSize(1024 * 1024);
        bean.setMaxBinaryMessageBufferSize(1024 * 1024);
        return bean;
    }
}
