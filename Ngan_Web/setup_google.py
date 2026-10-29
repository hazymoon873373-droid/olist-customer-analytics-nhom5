"""Import a Google OAuth Web client downloaded by its owner. Never print credentials."""
from argparse import ArgumentParser
import json
from pathlib import Path
import secrets
import tomllib

from google_auth import GOOGLE_METADATA, approved_roles, google_configuration


def build_settings(client, admins, analysts, redirect):
    web = client.get('web', {})
    if not web.get('client_id', '').endswith('.apps.googleusercontent.com') or not web.get('client_secret'):
        raise ValueError('Cần file JSON OAuth loại Web application từ Google Cloud.')
    if redirect not in web.get('redirect_uris', []):
        raise ValueError('Địa chỉ quay về chưa có trong cấu hình OAuth tải từ Google.')
    access = {'admins': admins, 'analysts': analysts}
    approved_roles(access)
    settings = {'auth': {'redirect_uri': redirect, 'cookie_secret': secrets.token_urlsafe(48),
                        'google': {'client_id':web['client_id'], 'client_secret':web['client_secret'], 'server_metadata_url':GOOGLE_METADATA}},
                'google_access':access}
    google_configuration(settings)
    auth = settings['auth']
    literal = lambda value: json.dumps(value, ensure_ascii=False)
    content = '\n'.join([
        '[auth]', f'redirect_uri = {literal(redirect)}', f'cookie_secret = {literal(auth["cookie_secret"])}',
        '', '[auth.google]', *[f'{key} = {literal(value)}' for key,value in auth['google'].items()],
        '', '[google_access]', f'admins = {literal(admins)}', f'analysts = {literal(analysts)}', '',
    ])
    # Validate serialization before writing the real configuration.
    assert google_configuration(tomllib.loads(content)) == approved_roles(access)
    return content


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--client-json', type=Path, required=True)
    parser.add_argument('--admin', action='append', required=True, help='Repeat for each authorized administrator.')
    parser.add_argument('--analyst', action='append', default=[])
    parser.add_argument('--redirect-uri', default='http://localhost:8501/oauth2callback')
    args = parser.parse_args()
    output = Path(__file__).resolve().parent / '.streamlit/secrets.toml'
    try:
        content = build_settings(json.loads(args.client_json.read_text(encoding='utf-8-sig')), args.admin, args.analyst, args.redirect_uri)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Existing secrets are never silently replaced or copied into a backup file.
        with output.open('x', encoding='utf8', newline='\n') as file:
            file.write(content)
    except FileExistsError:
        parser.exit(1, 'secrets.toml đã có; giữ nguyên. Mở file này để chỉnh cấu hình khi cần.\n')
    except (OSError, ValueError, TypeError, AttributeError):
        parser.exit(1, 'Không thể tạo cấu hình. Kiểm tra file JSON Web OAuth, redirect URI và danh sách email.\n')
    print('Đã lưu cấu hình riêng tại .streamlit/secrets.toml. Khởi động lại Streamlit để áp dụng.')
    print('Không chia sẻ hoặc đưa file JSON OAuth và secrets.toml lên GitHub.')


if __name__ == '__main__':
    main()
