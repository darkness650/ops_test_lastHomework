// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"crypto/subtle"
	"net/http"
	"os"
)

const adminSessionCookie = "shop_admin_session"

var (
	adminUsername     = envOrDefault("ADMIN_USERNAME", "admin")
	adminPassword     = envOrDefault("ADMIN_PASSWORD", "admin123")
	adminSessionToken = envOrDefault("ADMIN_SESSION_TOKEN", "online-boutique-admin")
)

func envOrDefault(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func validAdminCredentials(username, password string) bool {
	usernameMatch := subtle.ConstantTimeCompare([]byte(username), []byte(adminUsername))
	passwordMatch := subtle.ConstantTimeCompare([]byte(password), []byte(adminPassword))
	return usernameMatch == 1 && passwordMatch == 1
}

func isAdminAuthenticated(r *http.Request) bool {
	cookie, err := r.Cookie(adminSessionCookie)
	if err != nil {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(cookie.Value), []byte(adminSessionToken)) == 1
}

func setAdminSession(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name:     adminSessionCookie,
		Value:    adminSessionToken,
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
		MaxAge:   60 * 60 * 8,
	})
}

func clearAdminSession(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name:     adminSessionCookie,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
		MaxAge:   -1,
	})
}
