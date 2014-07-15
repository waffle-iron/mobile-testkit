//  Copyright (c) 2012 Couchbase, Inc.
//  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
//  except in compliance with the License. You may obtain a copy of the License at
//    http://www.apache.org/licenses/LICENSE-2.0
//  Unless required by applicable law or agreed to in writing, software distributed under the
//  License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
//  either express or implied. See the License for the specific language governing permissions
//  and limitations under the License.

package auth

import (
	"net/http"
	"time"

	"github.com/couchbaselabs/sync_gateway/base"
)

// A user login session (used with cookie-based auth.)
type LoginSession struct {
	ID         string    `json:"id"`
	Username   string    `json:"username"`
	Expiration time.Time `json:"expiration"`
	Ttl        string    `json:"ttl"`
}

const CookieName = "SyncGatewaySession"

func (auth *Authenticator) AuthenticateCookie(rq *http.Request, response http.ResponseWriter) (User, error) {
	cookie, _ := rq.Cookie(CookieName)
	if cookie == nil {
		return nil, nil
	}

	var session LoginSession
	err := auth.bucket.Get(docIDForSession(cookie.Value), &session)
	if err != nil {
		if base.IsDocNotFoundError(err) {
			err = nil
		}
		return nil, err
	}
	// Don't need to check session.Expiration, because Couchbase will have nuked the document.
        //update the session Expiration if 10% or more of the current expiration time has elapsed
        duration, _ := time.ParseDuration(session.Ttl)
	sessionPercentElapsed := int((time.Now().Add(duration).Sub(session.Expiration)).Seconds())
	tenPercentOfTtl := int(duration.Seconds())/10
        if(sessionPercentElapsed > tenPercentOfTtl) {
        	session.Expiration = time.Now().Add(duration)
        	ttlSec := int(duration.Seconds())
		if err = auth.bucket.Set(docIDForSession(session.ID), ttlSec, session); err != nil {
                	return nil, err
        	}

		cookie.Expires = session.Expiration
		http.SetCookie(response, cookie)
	}
	user, err := auth.GetUser(session.Username)
	if user != nil && user.Disabled() {
		user = nil
	}
	return user, err
}

func (auth *Authenticator) CreateSession(username string, ttl time.Duration) (*LoginSession, error) {
	ttlSec := int(ttl.Seconds())
	if ttlSec <= 0 {
		return nil, base.HTTPErrorf(400, "Invalid session time-to-live")
	}
	session := &LoginSession{
		ID:         base.GenerateRandomSecret(),
		Username:   username,
		Expiration: time.Now().Add(ttl),
		Ttl: ttl.String(),
	}
	if err := auth.bucket.Set(docIDForSession(session.ID), ttlSec, session); err != nil {
		return nil, err
	}
	return session, nil
}

func (auth *Authenticator) MakeSessionCookie(session *LoginSession) *http.Cookie {
	if session == nil {
		return nil
	}
	return &http.Cookie{
		Name:    CookieName,
		Value:   session.ID,
		Expires: session.Expiration,
	}
}

func (auth Authenticator) DeleteSessionForCookie(rq *http.Request) *http.Cookie {
	cookie, _ := rq.Cookie(CookieName)
	if cookie == nil {
		return nil
	}
	auth.bucket.Delete(docIDForSession(cookie.Value))

	newCookie := *cookie
	newCookie.Value = ""
	newCookie.Expires = time.Now()
	return &newCookie
}

func docIDForSession(sessionID string) string {
	return "_sync:session:" + sessionID
}
