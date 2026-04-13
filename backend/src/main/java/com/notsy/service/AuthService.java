package com.notsy.service;

import com.notsy.dto.request.LoginRequest;
import com.notsy.dto.request.RefreshTokenRequest;
import com.notsy.dto.request.RegisterRequest;
import com.notsy.dto.response.AuthResponse;
import com.notsy.entity.User;
import com.notsy.exception.ValidationException;
import com.notsy.repository.UserRepository;
import com.notsy.security.CustomUserDetailsService;
import com.notsy.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final AuthenticationManager authenticationManager;
    private final CustomUserDetailsService userDetailsService;

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new ValidationException("Email already registered");
        }

        User user = User.builder()
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .name(request.getName())
                .isActive(true)
                .build();

        user = userRepository.save(user);

        String accessToken = jwtUtil.generateToken(user.getEmail());
        String refreshToken = jwtUtil.generateRefreshToken(user.getEmail());

        return buildAuthResponse(accessToken, refreshToken, user);
    }

    public AuthResponse login(LoginRequest request) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword())
        );

        String accessToken = jwtUtil.generateToken(authentication);
        String refreshToken = jwtUtil.generateRefreshToken(request.getEmail());

        User user = userDetailsService.getUserByEmail(request.getEmail());

        return buildAuthResponse(accessToken, refreshToken, user);
    }

    public AuthResponse refresh(RefreshTokenRequest request) {
        if (!jwtUtil.validateToken(request.getRefreshToken())) {
            throw new ValidationException("Invalid refresh token");
        }

        String email = jwtUtil.getEmailFromToken(request.getRefreshToken());
        User user = userDetailsService.getUserByEmail(email);

        String accessToken = jwtUtil.generateToken(email);
        String refreshToken = jwtUtil.generateRefreshToken(email);

        return buildAuthResponse(accessToken, refreshToken, user);
    }

    public User getCurrentUser(String email) {
        return userDetailsService.getUserByEmail(email);
    }

    private AuthResponse buildAuthResponse(String accessToken, String refreshToken, User user) {
        return AuthResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .user(AuthResponse.UserResponse.builder()
                        .id(user.getId())
                        .email(user.getEmail())
                        .name(user.getName())
                        .profilePic(user.getProfilePic())
                        .createdAt(user.getCreatedAt())
                        .build())
                .timestamp(java.time.LocalDateTime.now())
                .build();
    }
}
