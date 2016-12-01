from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from zentral.core.probes.models import ProbeSource


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class OsqueryComplianceProbeViewsTestCase(TestCase):
    def test_create_probe_get(self):
        response = self.client.get(reverse("osquery:create_compliance_probe"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/probes/form.html")
        self.assertContains(response, "Create osquery compliance probe")

    def test_create_probe_error(self):
        response = self.client.post(reverse("osquery:create_probe"), {})
        self.assertFormError(response, "form", "name", "This field is required.")

    def create_probe(self, **kwargs):
        response = self.client.post(reverse("osquery:create_compliance_probe"),
                                    kwargs,
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "osquery/compliance_probe.html")
        self.assertIn("probe", response.context)
        probe = response.context["probe"]
        self.assertIn("object", response.context)
        probe_source = response.context["object"]
        return response, probe_source, probe

    def test_create_probe(self):
        name = "234390824"
        response, probe_source, probe = self.create_probe(name=name)
        self.assertContains(response, name)
        self.assertEqual(probe.get_model(), "OsqueryComplianceProbe")
        self.assertContains(response, reverse("osquery:add_compliance_probe_preference_file", args=(probe.pk,)))
        self.assertContains(response, reverse("osquery:add_compliance_probe_file_checksum", args=(probe.pk,)))
        self.assertEqual(probe.name, name)
        self.assertEqual(probe_source.name, name)
        self.assertEqual(probe_source.pk, probe.pk)

    def test_index(self):
        name = "2343908241"
        _, probe_source, probe = self.create_probe(name=name)
        response = self.client.get(reverse("probes:index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, name)
        probe_source.status = ProbeSource.ACTIVE
        probe_source.save()
        response = self.client.get(reverse("probes:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, name)

    # preference files

    def test_add_preference_file_get(self):
        _, _, probe = self.create_probe(name="name")
        response = self.client.get(reverse("osquery:add_compliance_probe_preference_file", args=(probe.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "osquery/preference_file_form.html")
        self.assertContains(response, "Add compliance probe preference file")

    def prepare_preference_file_post_data(self, probe_pk, **kwargs):
        response = self.client.get(reverse("osquery:add_compliance_probe_preference_file", args=(probe_pk,)))
        form = response.context["key_form_set"]
        d = {}
        prefix = form.management_form.prefix
        for k, v in form.management_form.initial.items():
            d["{}-{}".format(prefix, k)] = v
        for k, v in kwargs.items():
            if k in ("rel_path", "type", "interval"):
                d["pff-{}".format(k)] = v
            else:
                d["kfs-0-{}".format(k)] = v
        return d

    def test_add_preference_file_error(self):
        _, _, probe = self.create_probe(name="name")
        post_data = self.prepare_preference_file_post_data(probe.pk)
        response = self.client.post(reverse("osquery:add_compliance_probe_preference_file", args=(probe.pk,)),
                                    post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "osquery/preference_file_form.html")
        self.assertFormError(response, "preference_file_form", "rel_path", "This field is required.")
        self.assertFormError(response, "preference_file_form", "type", "This field is required.")
        self.assertFormError(response, "preference_file_form", "interval", "This field is required.")
        self.assertFormsetError(response, "key_form_set", 0, "key", "This field is required.")
        self.assertFormsetError(response, "key_form_set", 0, "test", "This field is required.")

    def create_osquery_probe_with_extra_preference_file(self, **kwargs):
        _, probe_source, probe = self.create_probe(name="godzilla63")
        post_data = self.prepare_preference_file_post_data(probe.pk, **kwargs)
        response = self.client.post(reverse("osquery:add_compliance_probe_preference_file", args=(probe.pk,)),
                                    post_data,
                                    follow=True)
        self.assertRedirects(response, "{}#preference_files".format(probe_source.get_absolute_url()))
        return response, response.context["probe"], probe_source

    def test_add_preference_file(self):
        response, probe, probe_source = self.create_osquery_probe_with_extra_preference_file(type="USERS",
                                                                                             rel_path="Bluetooth",
                                                                                             interval=34,
                                                                                             key="ZU",
                                                                                             test="EQ",
                                                                                             arg_r="ZU KEY VAL")
        self.assertEqual(len(probe.preference_files), 1)
        self.assertEqual(probe.preference_files[0].rel_path, "Bluetooth")
        self.assertEqual(probe.preference_files[0].interval, 34)
        self.assertEqual(probe.preference_files[0].type, "USERS")
        self.assertEqual(probe.preference_files[0].keys[0].key, "ZU")
        self.assertEqual(probe.preference_files[0].keys[0].value, "ZU KEY VAL")
        self.assertNotContains(response,
                               reverse("osquery:delete_compliance_probe_preference_file", args=(probe.pk, 0)))

    def test_edit_preference_file_get(self):
        response, probe, probe_source = self.create_osquery_probe_with_extra_preference_file(type="USERS",
                                                                                             rel_path="Bluetooth",
                                                                                             interval=34,
                                                                                             key="ZU",
                                                                                             test="INT_GTE_LTE",
                                                                                             arg_l=1,
                                                                                             arg_r=6)
        self.assertContains(response, reverse("osquery:update_compliance_probe_preference_file", args=(probe.pk, 0)))
        response = self.client.get(reverse("osquery:update_compliance_probe_preference_file", args=(probe.pk, 0)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update compliance probe preference file")

    def test_edit_preference_file(self):
        kwargs = dict(type="USERS", rel_path="Bluetooth", interval=34, key="ZU", test="INT_GTE_LTE", arg_l=1, arg_r=6)
        response, probe, probe_source = self.create_osquery_probe_with_extra_preference_file(**kwargs)
        kwargs["arg_r"] = 567
        post_data = self.prepare_preference_file_post_data(probe.pk, **kwargs)
        response = self.client.post(reverse("osquery:update_compliance_probe_preference_file", args=(probe.pk, 0)),
                                    post_data,
                                    follow=True)
        self.assertRedirects(response, "{}#preference_files".format(probe_source.get_absolute_url()))
        probe = response.context["probe"]
        self.assertEqual(len(probe.preference_files), 1)
        self.assertEqual(probe.preference_files[0].rel_path, "Bluetooth")
        self.assertEqual(probe.preference_files[0].interval, 34)
        self.assertEqual(probe.preference_files[0].type, "USERS")
        self.assertEqual(probe.preference_files[0].keys[0].key, "ZU")
        self.assertEqual(probe.preference_files[0].keys[0].min_value, 1)
        self.assertEqual(probe.preference_files[0].keys[0].max_value, 567)

    # dicovery

    def test_add_file_checksum_get(self):
        _, _, probe = self.create_probe(name="name")
        response = self.client.get(reverse("osquery:add_compliance_probe_file_checksum", args=(probe.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "osquery/file_checksum_form.html")
        self.assertContains(response, "Add compliance probe file checksum")

    def test_add_file_checksum_error(self):
        _, _, probe = self.create_probe(name="name")
        response = self.client.post(reverse("osquery:add_compliance_probe_file_checksum", args=(probe.pk,)), {})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "path", "This field is required.")
        self.assertFormError(response, "form", "sha256", "This field is required.")
        self.assertFormError(response, "form", "interval", "This field is required.")

    def create_osquery_probe_with_file_checksum(self, path, sha256, interval):
        _, probe_source, probe = self.create_probe(name="name")
        response = self.client.post(reverse("osquery:add_compliance_probe_file_checksum", args=(probe.pk,)),
                                    {"path": path, "sha256": sha256, "interval": interval},
                                    follow=True)
        self.assertRedirects(response, "{}#file_checksums".format(probe_source.get_absolute_url()))
        return response, response.context["probe"], probe_source

    def test_add_file_checksum(self):
        path = "zu"
        sha256 = 64 * "0"
        interval = 17
        response, probe, probe_source = self.create_osquery_probe_with_file_checksum(path, sha256, interval)
        self.assertEqual(len(probe.file_checksums), 1)
        self.assertEqual(probe.file_checksums[0].path, path)
        self.assertEqual(probe.file_checksums[0].sha256, sha256)
        self.assertEqual(probe.file_checksums[0].interval, interval)

    def test_edit_file_checksum_get(self):
        path = "zu"
        sha256 = 64 * "0"
        interval = 17
        response, probe, probe_source = self.create_osquery_probe_with_file_checksum(path, sha256, interval)
        response = self.client.get(reverse("osquery:update_compliance_probe_file_checksum", args=(probe.pk, 0)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update compliance probe file checksum")

    def test_edit_file_checksum(self):
        path = "zu"
        sha256 = 64 * "0"
        interval = 17
        response, probe, probe_source = self.create_osquery_probe_with_file_checksum(path, sha256, interval)
        new_sha256 = 64 * "1"
        response = self.client.post(reverse("osquery:update_compliance_probe_file_checksum", args=(probe.pk, 0)),
                                    {"path": path, "sha256": new_sha256, "interval": interval},
                                    follow=True)
        self.assertRedirects(response, "{}#file_checksums".format(probe_source.get_absolute_url()))
        probe = response.context["probe"]
        self.assertEqual(len(probe.file_checksums), 1)
        self.assertEqual(probe.file_checksums[0].sha256, new_sha256)

    def test_delete_file_checksum_not_possible(self):
        # probe with only one file checksum
        path = "zu"
        sha256 = 64 * "0"
        interval = 17
        response, probe, probe_source = self.create_osquery_probe_with_file_checksum(path, sha256, interval)
        response = self.client.get(reverse("osquery:delete_compliance_probe_file_checksum", args=(probe.pk, 0)))
        self.assertRedirects(response, "{}#osquery_compliance".format(probe_source.get_absolute_url()))

    def test_delete_file_checksum_get(self):
        path = "zu"
        sha256 = 64 * "0"
        interval = 17
        response, probe, probe_source = self.create_osquery_probe_with_file_checksum(path, sha256, interval)
        self.assertNotContains(response, reverse("osquery:delete_compliance_probe_file_checksum", args=(probe.pk, 0)))
        # extra file checksum
        response = self.client.post(reverse("osquery:add_compliance_probe_file_checksum", args=(probe.pk,)),
                                    {"path": path[::-1], "sha256": sha256, "interval": interval},
                                    follow=True)
        self.assertRedirects(response, "{}#file_checksums".format(probe_source.get_absolute_url()))
        probe = response.context["probe"]
        self.assertEqual(len(probe.file_checksums), 2)
        self.assertContains(response, reverse("osquery:delete_compliance_probe_file_checksum", args=(probe.pk, 0)))
        response = self.client.get(reverse("osquery:delete_compliance_probe_file_checksum", args=(probe.pk, 0)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete compliance probe file checksum")

    def test_delete_file_checksum_post(self):
        path = "zu"
        sha256 = 64 * "0"
        interval = 17
        response, probe, probe_source = self.create_osquery_probe_with_file_checksum(path, sha256, interval)
        # extra file checksum
        response = self.client.post(reverse("osquery:add_compliance_probe_file_checksum", args=(probe.pk,)),
                                    {"path": path[::-1], "sha256": sha256, "interval": interval},
                                    follow=True)
        response = self.client.post(reverse("osquery:delete_compliance_probe_file_checksum", args=(probe.pk, 0)),
                                    follow=True)
        self.assertRedirects(response, "{}#osquery_compliance".format(probe_source.get_absolute_url()))
        probe = response.context["probe"]
        self.assertEqual(len(probe.file_checksums), 1)
        self.assertEqual(probe.file_checksums[0].path, path[::-1])
