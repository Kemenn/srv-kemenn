source_dir="srv-kemenn"
destination="srv-kemenn.deb"
username="user"

if [ -e "$destination" ]; then
    rm "$destination"
fi
chown -R root:root "$source_dir/"
chown -R www-data:www-data "$source_dir/etc/kemenn/"
chmod -R 755 "$source_dir/DEBIAN/"

dpkg-deb --build "$source_dir/"
chown "$username" "$destination"
chgrp "$username" "$destination"
chmod 755 "$destination"

chown -R "$username:$username" "$source_dir/"
