package com.nicehash.connect;

import org.apache.commons.codec.binary.Hex;
import org.apache.http.HttpHeaders;
import org.apache.http.HttpResponse;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpDelete;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.*;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

public class Api {

	private static final Charset CHARSET = StandardCharsets.ISO_8859_1;
	private static final String HMAC_SHA256 = "HmacSHA256";

	private String urlRoot;
	private String orgId;
	private String apiKey;
	private String apiSecret;

	public Api(String urlRoot, String orgId, String apiKey, String apiSecret) {
		this.urlRoot = urlRoot;
		this.orgId = orgId;
		this.apiKey = apiKey;
		this.apiSecret = apiSecret;
	}

	private static String hashBySegments(String key, String apiKey, String time, String nonce, String orgId, String method, String encodedPath, String query, String bodyStr) {
		List<byte []> segments = Arrays.asList(
				apiKey.getBytes(CHARSET),
				time.getBytes(CHARSET),
				nonce.getBytes(CHARSET),
				null,  // unused field
				orgId.getBytes(CHARSET),
				null,  // unused field
				method.getBytes(CHARSET),
				encodedPath == null ? null : encodedPath.getBytes(CHARSET),
				query == null ? null : query.getBytes(CHARSET));

		if (bodyStr != null && bodyStr.length() > 0) {
			segments = new ArrayList<>(segments);
			segments.add(bodyStr.getBytes(StandardCharsets.UTF_8));
		}
		return hmacSha256BySegments(key, segments);
	}

	private static String hmacSha256BySegments(String key, List<byte []> segments) {
		try {
			Mac mac = Mac.getInstance(HMAC_SHA256);
			SecretKeySpec secret_key = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), HMAC_SHA256);
			mac.init(secret_key);
			boolean first = true;

			for (byte [] segment: segments) {

				if (!first) {
					mac.update((byte) 0);
				} else {
					first = false;
				}

				if (segment != null) {
					mac.update(segment);
				}
			}

			return Hex.encodeHexString(mac.doFinal());
		} catch (Exception e) {
			throw new RuntimeException("Cannot create HmacSHA256", e);
		}
	}

	public String get(String url) {
		return this.get(url, false, null);
	}

	public String get(String url, boolean auth, String time) {
		StringBuffer result = new StringBuffer();
		HttpClient client = HttpClientBuilder.create().build();
		HttpGet request = new HttpGet(this.urlRoot+url);

		if (auth) {
			String nonce  = UUID.randomUUID().toString();
			String digest = Api.hashBySegments(this.apiSecret, this.apiKey, time, nonce, this.orgId, request.getMethod(), request.getURI().getPath(), request.getURI().getQuery(), null);

			request.setHeader("X-Time", time);
			request.setHeader("X-Nonce", nonce);
			request.setHeader("X-Auth", this.apiKey+":"+digest);
			request.setHeader("X-Organization-Id", this.orgId);
		}

		try {
			HttpResponse response = client.execute(request);
			BufferedReader rd = new BufferedReader(new InputStreamReader(response.getEntity().getContent()));

			String line = "";
			while ((line = rd.readLine()) != null) {
				result.append(line);
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
		return result.toString();
	}

	public String post(String url, String payload, String time, boolean requestId) {
		StringBuffer result = new StringBuffer();
		HttpClient client = HttpClientBuilder.create().build();
		HttpPost request = new HttpPost(this.urlRoot+url);

		StringEntity entity = null;
		if (payload != null) {
			try {
				entity = new StringEntity(payload);
			} catch (UnsupportedEncodingException e) {
				e.printStackTrace();
			}
		}

		request.setEntity(entity);
		request.setHeader("Accept", "application/json");
		request.setHeader("Content-type", "application/json");

		String nonce  = UUID.randomUUID().toString();
		String digest = Api.hashBySegments(this.apiSecret, this.apiKey, time, nonce, this.orgId, request.getMethod(), request.getURI().getPath(), request.getURI().getQuery(), payload);

		request.setHeader("X-Time", time);
		request.setHeader("X-Nonce", nonce);
		request.setHeader("X-Auth", this.apiKey+":"+digest);
		request.setHeader("X-Organization-Id", this.orgId);
		if (requestId)
			request.setHeader("X-Request-Id", UUID.randomUUID().toString()); //must be unique request

		try {
			HttpResponse response = client.execute(request);
			BufferedReader rd = new BufferedReader(new InputStreamReader(response.getEntity().getContent()));

			String line = "";
			while ((line = rd.readLine()) != null) {
				result.append(line);
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
		return result.toString();
	}

	public String delete(String url, String time, boolean requestId) {
		StringBuffer result = new StringBuffer();
		HttpClient client = HttpClientBuilder.create().build();
		HttpDelete request = new HttpDelete(this.urlRoot+url);

		String nonce  = UUID.randomUUID().toString();
		String digest = Api.hashBySegments(this.apiSecret, this.apiKey, time, nonce, this.orgId, request.getMethod(), request.getURI().getPath(), request.getURI().getQuery(), null);

		request.setHeader("X-Time", time);
		request.setHeader("X-Nonce", nonce);
		request.setHeader("X-Auth", this.apiKey+":"+digest);
		request.setHeader("X-Organization-Id", this.orgId);
		if (requestId)
			request.setHeader("X-Request-Id", UUID.randomUUID().toString()); //must be unique request

		try {
			HttpResponse response = client.execute(request);
			BufferedReader rd = new BufferedReader(new InputStreamReader(response.getEntity().getContent()));

			String line = "";
			while ((line = rd.readLine()) != null) {
				result.append(line);
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
		return result.toString();
	}
}
